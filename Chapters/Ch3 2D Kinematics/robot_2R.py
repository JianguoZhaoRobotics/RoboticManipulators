XML_2R = """
<mujoco model="2R_planar_robot">

  <!-- No gravity: kinematics only -->
  <option gravity="0 0 0"/>

  <!-- ====================================================================
       SCENE APPEARANCE
       visual : global rendering settings (lighting, haze)
       asset  : textures and materials — referenced by geoms via material=""
  ==================================================================== -->
  <visual>
    <!-- headlight = flashlight attached to the camera.
         ambient prevents fully-shadowed areas from being pitch black. -->
    <headlight diffuse="0.5 0.5 0.5" ambient="0.3 0.3 0.3" specular="0.0 0.0 0.0"/>
    <!-- haze blends the far background with this blue-grey colour -->
    <rgba haze="0.15 0.25 0.35 1"/>
  </visual>

  <asset>
    <!-- Two-tone blue checkerboard floor texture.
         builtin="checker" generates the pattern entirely inside MuJoCo —
         no external image file needed.
         rgb1 / rgb2 = the two alternating tile colours. -->
    <texture name="floor_tex" type="2d" builtin="checker"
             rgb1="0.15 0.25 0.38" rgb2="0.22 0.38 0.55"
             width="512" height="512"/>
    <!-- Material wraps the texture and adds surface properties.
         texrepeat="6 6" tiles the checker 6 times per unit length.
         reflectance adds a subtle mirror-like sheen. -->
    <material name="floor_mat" texture="floor_tex" texrepeat="6 6"
              reflectance="0.2" shininess="0.1"/>

    <!-- Gradient skybox: blue at the horizon, dark at the top.
         type="skybox" tells MuJoCo to use this as the scene background. -->
    <texture name="skybox" type="skybox" builtin="gradient"
             rgb1="0.3 0.5 0.7" rgb2="0.05 0.05 0.15"
             width="512" height="512"/>
  </asset>

  <worldbody>

    <!-- Overhead directional light.
         dir points slightly off-axis for a natural look.
         castshadow="true" lets the links cast shadows on the floor. -->
    <light name="sun" pos="1 1 5" dir="-0.2 -0.2 -1"
           diffuse="0.8 0.8 0.8" specular="0.2 0.2 0.2" castshadow="true"/>

    <!-- Infinite ground plane with checker material.
         size="10 10 0.1" sets the half-extents of the rendered area.
         pos z=-0.02 places the floor just below the robot (which lives at z=0). -->
    <geom name="floor" type="plane" size="10 10 0.1" pos="0 0 -0.1"
          material="floor_mat"/>

    <!-- Top-down camera looking straight down the z-axis.
         pos    = (0, 0, 5) -- 5 m above the origin
         xyaxes = camera x-axis then y-axis in world frame;
                  "1 0 0  0 1 0" makes the camera look along -z (downward) -->
    <camera name="top" pos="0 0 5" xyaxes="1 0 0 0 1 0"/>

    <!-- Small cylinder marks the base (joint 1 location) -->
    <geom name="base_marker" type="cylinder" pos="0 0 0"
          size="0.07 0.07" rgba="0.15 0.15 0.15 1"/>

    <!-- =====================================================================
         LINK 1
         pos="0 0 0"  : link1 origin at the world origin
         joint1       : hinge (revolute) around the z-axis
    ===================================================================== -->
    <body name="link1" pos="0 0 0">
      <joint name="joint1" type="hinge" axis="0 0 1" pos="0 0 0"/>

      <!-- Capsule for link 1 (inset slightly so joint markers stay visible) -->
      <geom name="geom_link1" type="capsule"
            fromto="0.06 0 0   0.94 0 0"
            size="0.04" rgba="0.25 0.47 0.80 1"/>

      <!-- Elbow marker at the tip of link 1 -->
      <geom name="elbow_marker" type="cylinder" pos="1.0 0 0"
            size="0.07 0.07" rgba="0.15 0.15 0.15 1"/>

      <!-- ===================================================================
           LINK 2
           pos="1.0 0 0"  : link2 origin at the elbow
           joint2          : hinge around z, relative to link1
      =================================================================== -->
      <body name="link2" pos="1.0 0 0">
        <joint name="joint2" type="hinge" axis="0 0 1" pos="0 0 0"/>

        <!-- Capsule for link 2 (length 0.8 m) -->
        <geom name="geom_link2" type="capsule"
              fromto="0.06 0 0   0.74 0 0"
              size="0.04" rgba="0.80 0.25 0.25 1"/>

        <!-- =================================================================
             END-EFFECTOR
             pos="0.8 0 0"  : tip of link 2, rigidly attached (no joint)
        ================================================================= -->
        <body name="end_effector" pos="0.8 0 0">
          <geom name="ee_marker" type="sphere" size="0.08" rgba="0.0 0.75 0.0 1"/>
        </body>

      </body>   <!-- end link2 -->
    </body>     <!-- end link1 -->

  </worldbody>
</mujoco>
"""