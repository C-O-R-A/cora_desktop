sudo apt install \
         ros-jazzy\
         ros-jazzy-ros2-control\
         ros-jazzy-ros2-controllers\
         ros-jazzy-moveit\
         ros-jazzy-moveit-py\
         ros-jazzy-moveit-servo\
         ros-jazzy-gazebo-ros2-control\
         ros-jazzy-gazebo-ros2-control-plugins\
         ros-jazzy-gazebo-ros2-control-msgs\

sudo apt-get install ros-${ROS_DISTRO}-ros-gz
  ros-${ROS_DISTRO}-gazebo-ros-pkgs \
  ros-${ROS_DISTRO}-gz-ros2-control \


sudo rosdep-install

pip install -r requirements.txt

sudo apt update && sudo apt upgrade

cd .. && colcon build --symlink-install

source /opt/ros/jazzy/setup.bash
echo "source /opt/ros/jazzy/setup.bash" >> ./bashrc
source /install/setup.bash
echo "source /install/setup.bash" >> ./bashrc
export LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# set -e

# echo "Setting ethernet hostname to cora"
# sudo hostnamectl set-hostname cora

# echo "Installing Avahi"
# sudo apt update
# sudo apt install -y avahi-daemon

# echo "Enabling Avahi"
# sudo systemctl enable avahi-daemon
# sudo systemctl start avahi-daemon

# echo "Done. Reboot recommended."

# run with: './install.sh'

# NOTES
# To get the moveit setup assistant working in vscode, unset the gtk path using 'unset GTK_PATH'
#
# Make sure cmake file contains:
#
# install(
#   DIRECTORY
#       <folder_name>
#   DESTINATION share/${PROJECT_NAME}
# )
#
# Also make sure onshape config files are in the source root and point to 'description_pkg/meshes/' and not to 'meshes/'
# 
# if the setup assistant segfaults after clicking load model, install older rviz snapshot: https://github.com/moveit/moveit2/issues/3546#issuecomment-32666
#   wget http://snapshots.ros.org/jazzy/2025-05-23/ubuntu/pool/main/r/ros-jazzy-rviz-common/ros-jazzy-rviz-common_14.1.11-1noble.20250520.201719_amd64.deb
#
#   sudo apt --fix-broken install
#
#   sudo dpkg -i ros-jazzy-rviz-common_14.1.11-1noble.20250520.201719_amd64.deb
#
#
# You must add accell limits to joint limits config file
#
# End effector should have parent link L5, not end effector
#
# In controllers.yaml, for the gripperaction controller, 'joints' --> 'joint'


        <!-- <gazebo reference="Camera" >
            <sensor name="Camera" type="camera">
                <camera>
                    <horizontal_fov>0.86</horizontal_fov>
                    <image>
                        <width>1280</width>
                        <height>720</height>
                        <!-- <format>R8G8B8</format> -->
                    </image>
                    <clip>
                        <near>0.02</near>
                        <far>300</far>
                    </clip>
                    <noise>
                        <type>gaussian</type>
                        <mean>0.0</mean>
                        <stddev>0.007</stddev>
                    </noise>
                </camera>
                <always_on>1</always_on>
                <gz_frame_id>Camera_frame</gz_frame_id>
                <topic>gz_gripper_cam</topic>
                <update_rate>30.0</update_rate>
                <visualize>true</visualize>
            </sensor>
        </gazebo> -->

