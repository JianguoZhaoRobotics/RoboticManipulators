import time
import numpy as np
from lerobot.motors.feetech import FeetechMotorsBus, OperatingMode
from lerobot.motors import Motor, MotorNormMode

TICKS_PER_REV = 4096
HOME_TICK     = 2048


def deg_to_ticks(deg):
    """Convert an angle in degrees to STS3215 encoder ticks."""
    return int(HOME_TICK + round(deg * TICKS_PER_REV / 360.0))


def ticks_to_deg(ticks):
    """Convert STS3215 encoder ticks to degrees."""
    return (ticks - HOME_TICK) * 360.0 / TICKS_PER_REV


def _flush(bus, wait=0.1):
    # Wait briefly then clear the serial receive buffer so leftover bytes
    # from a previous command do not corrupt the next read.
    time.sleep(wait)
    bus.port_handler.clearPort()


# ── Connect / disconnect any number of motors ───────────────────────────────────
# These work for one motor, two motors, or more -- the same functions are used
# throughout Part 1 (one motor), Part 2 (two motors), and the three-motor problem.
def connect_motors(port, motor_ids, mode=OperatingMode.POSITION):
    """Connect to one or more motors daisy-chained on the same port.

    motor_ids : a single motor ID (e.g. 1), or a list of IDs for several motors
                on the same bus (e.g. [1, 2] or [1, 2, 3]). Motors are addressed
                internally as "motor1", "motor2", ... in the order given.
    mode      : OperatingMode.POSITION (default) or OperatingMode.VELOCITY.

    A lone motor is reset to its 0° home position on connect, giving a known
    starting state. Multiple motors are NOT reset, since a hard reset could
    snap a mechanically linked joint through an unexpected motion.

    Returns a `bus` object to pass to write_angles / write_speeds, read_angles,
    and disconnect_motors.
    """
    ids   = [motor_ids] if isinstance(motor_ids, int) else list(motor_ids)
    names = [f"motor{i + 1}" for i in range(len(ids))]

    bus = FeetechMotorsBus(
        port=port,
        motors={n: Motor(mid, "sts3215", MotorNormMode.DEGREES) for n, mid in zip(names, ids)},
    )
    bus.motor_names = names   # remembered so read_angles/disconnect_motors know what's on the bus

    bus.connect(len(ids) == 1)   # reset-to-0° only for a single, unlinked motor
    _flush(bus, 0.25 if len(ids) == 1 else 0.3)
    for n in names:
        bus.write("Operating_Mode", n, mode.value, num_retry=3)
        _flush(bus, 0.1)
        bus.write("Torque_Enable", n, 1, num_retry=3)
        _flush(bus, 0.15 if len(ids) == 1 else 0.2)
    return bus


def connect_motors_velocity(port, motor_ids):
    """Same as connect_motors, but switches to velocity (wheel) mode instead of position mode."""
    return connect_motors(port, motor_ids, mode=OperatingMode.VELOCITY)


def disconnect_motors(bus):
    """Disable torque on every motor on the bus and close the connection."""
    for n in bus.motor_names:
        try:
            bus.write("Torque_Enable", n, 0, num_retry=3)
            _flush(bus, 0.1)
        except Exception:
            pass
    bus.disconnect()
    print("Motor disconnected." if len(bus.motor_names) == 1 else "Motors disconnected.")


def force_disconnect(*bus_vars):
    """Use after a crash to release the COM port: force_disconnect(bus)"""
    for b in bus_vars:
        try:
            b.disconnect()
            print("Motor disconnected.")
        except Exception as e:
            print(f"Already closed ({e})")


# ── Assign / verify motor IDs ────────────────────────────────────────────────
# Only one motor should be connected to the bus while these run -- if two
# motors on the bus share the same ID they both respond to every command and
# cannot be told apart.
def read_motor_id(port, motor_id):
    """Connect to a motor assumed to be at `motor_id` and read back its ID register.

    Handy as a sanity check -- e.g. after power-cycling following write_motor_id,
    call read_motor_id(port, new_id) to confirm the new ID was saved permanently.
    """
    bus = FeetechMotorsBus(
        port=port,
        motors={"motor": Motor(motor_id, "sts3215", MotorNormMode.DEGREES)},
    )
    bus.connect(False)  # connect without initializing
    current_id = bus.read("ID", "motor")
    bus.port_handler.closePort()
    return current_id


def write_motor_id(port, current_id, new_id, existing_ids=None):
    """Reassign a motor's ID on the bus.

    current_id   : the motor's existing ID (factory default is 1)
    new_id       : the ID to assign
    existing_ids : IDs already assigned to other motors on the same bus
                   (e.g. [MOTOR_ID_1]). If new_id matches one of these, the
                   write is refused -- two motors sharing an ID would both
                   respond to every command and could no longer be addressed
                   separately.

    After writing, power-cycle the motor (unplug/replug the 12V supply) to
    save the new ID permanently.
    """
    if existing_ids is not None and new_id != current_id and new_id in existing_ids:
        raise ValueError(
            f"NEW_ID {new_id} is already used by another motor on this bus {list(existing_ids)}. "
            "Two motors cannot share the same ID -- choose a different NEW_ID."
        )

    if current_id == new_id:
        print(f"Motor ID is already {current_id}. No change made.")
        return

    bus = FeetechMotorsBus(
        port=port,
        motors={"motor": Motor(current_id, "sts3215", MotorNormMode.DEGREES)},
    )
    bus.connect(False)  # connect without initializing

    # The ID register lives in EEPROM, which the motor write-protects (Lock=1)
    # by default. Writing to a locked EEPROM register is silently ignored --
    # the motor still ACKs the packet, so no error is raised even though the ID
    # never actually changes. Unlock EEPROM first so the write takes effect.
    bus.write("Lock", "motor", 0, num_retry=3)
    _flush(bus, 0.1)
    bus.write("ID", "motor", new_id, num_retry=3)
    _flush(bus, 0.1)
    bus.port_handler.closePort()

    # The motor now answers on new_id, not current_id -- reconnect under the
    # new ID to re-lock EEPROM (protects against accidental future writes).
    bus2 = FeetechMotorsBus(
        port=port,
        motors={"motor": Motor(new_id, "sts3215", MotorNormMode.DEGREES)},
    )
    bus2.connect(False)
    bus2.write("Lock", "motor", 1, num_retry=3)
    bus2.port_handler.closePort()

    print(f"Motor ID changed: {current_id} → {new_id}")
    print("Power-cycle the motor now to save the new ID permanently.")


def scan_motor_id(port):
    """Detect the ID of the single motor connected to the bus, without needing to
    know it in advance.

    Broadcasts a ping to every possible ID and returns the ID of the one motor
    that answers. Raises a ConnectionError if no motor responds, or if more than
    one does (only one motor should be connected to the bus while scanning/
    assigning IDs).
    """
    bus = FeetechMotorsBus(port=port, motors={})
    bus.connect(False)  # connect without a handshake -- we don't know the ID yet
    found = bus.broadcast_ping(num_retry=3)
    bus.port_handler.closePort()

    if not found:
        raise ConnectionError(
            "No motor responded on the bus. Check that a motor is powered and connected."
        )
    if len(found) > 1:
        raise ConnectionError(
            f"Multiple motors responded on the bus: {sorted(found)}. "
            "Disconnect all but the motor you want to re-ID before scanning."
        )
    return next(iter(found))


def assign_motor_id(port, existing_ids=None):
    """Interactively reassign the ID of the single motor connected to the bus.

    Reads the motor's current ID automatically (via scan_motor_id -- no need to
    know it beforehand), prints it, then prompts for the new ID to assign. Reuses
    write_motor_id to perform the write, so a new_id already in existing_ids is
    refused and you're asked to try again.

    Returns the new ID once the write succeeds.
    """
    current_id = scan_motor_id(port)
    print(f"Found motor with ID {current_id}.")

    while True:
        raw = input("Enter the new ID for this motor (1-253): ").strip()
        try:
            new_id = int(raw)
            if not (1 <= new_id <= 253):
                raise ValueError
        except ValueError:
            print("Please enter a whole number between 1 and 253.")
            continue

        try:
            write_motor_id(port, current_id, new_id, existing_ids=existing_ids)
        except ValueError as e:
            print(e)
            continue
        return new_id




# ── Command / read any number of motors ─────────────────────────────────────────
def write_angles(bus, *degs):
    """Command every motor on the bus to move to a target angle (degrees), all at
    once, in a single packet. Pass one angle per motor, in the order used when
    connecting:

        write_angles(bus, 30)          # one motor
        write_angles(bus, 30, -45)     # two motors
    """
    targets = {f"motor{i + 1}": deg_to_ticks(d) for i, d in enumerate(degs)}
    bus.sync_write("Goal_Position", targets, normalize=False)
    _flush(bus, 0.03)


def write_speeds(bus, *speeds):
    """Command every motor on the bus to spin at a speed (wheel-mode units,
    range -1000..+1000), all at once. Pass one speed per motor, in the order
    used when connecting -- same calling convention as write_angles."""
    targets = {f"motor{i + 1}": s for i, s in enumerate(speeds)}
    bus.sync_write("Goal_Velocity", targets, normalize=False)
    _flush(bus, 0.03)


def read_angles(bus):
    """Read the current angle(s) of every motor on the bus, in degrees.

    Returns a single float if the bus has one motor, or a tuple (one value per
    motor, in connection order) if it has several:

        deg    = read_angles(bus)      # one motor
        d1, d2 = read_angles(bus)      # two motors
    """
    for attempt in range(6):
        try:
            _flush(bus, 0.02)
            raw  = bus.sync_read("Present_Position", normalize=False, num_retry=5)
            degs = tuple(ticks_to_deg(raw[n]) for n in bus.motor_names)
            return degs[0] if len(degs) == 1 else degs
        except Exception:
            if attempt == 5:
                raise
            time.sleep(0.05 * (attempt + 2))
            bus.port_handler.clearPort()


def move_to_angle_and_record(bus, target_deg, record_sec=3.0, sample_hz=50):
    """Send a position command to a single-motor bus, then record angle vs. time
    for record_sec seconds (target rate: sample_hz).

    Stops on elapsed wall-clock time rather than a fixed sample count -- a
    single read_angles() round trip can take longer than 1/sample_hz, so a
    fixed count would make the recording run longer than record_sec actually
    asks for. This way record_sec means what it says even if the achieved
    rate falls short of sample_hz.

    Returns:
        times     -- array of timestamps in seconds
        positions -- array of measured angles in degrees
    """
    dt = 1.0 / sample_hz
    times_list     = []
    positions_list = []

    write_angles(bus, target_deg)
    t_start = time.time()

    while True:
        tick  = time.time()
        t_now = tick - t_start
        if t_now >= record_sec:
            break
        positions_list.append(read_angles(bus))
        times_list.append(t_now)
        elapsed = time.time() - tick
        if elapsed < dt:
            time.sleep(dt - elapsed)

    return np.array(times_list), np.array(positions_list)
