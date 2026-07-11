#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="$ROOT/src"
BASHRC="$HOME/.bashrc"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"

if [ ! -d "$SRC_DIR" ]; then
  echo "ERROR: expected workspace root at $ROOT with a src/ folder."
  exit 1
fi

if [ "$(id -u)" -eq 0 ]; then
  echo "WARNING: running as root is not recommended. The script will still use sudo for system installs."
fi

echo "Workspace root: $ROOT"
echo "ROS distro: $ROS_DISTRO"

if [ -f "$ROOT/.gitmodules" ] || [ -f "$SRC_DIR/.gitmodules" ]; then
  echo "Updating git submodules..."
  git submodule update --init --recursive
fi

sudo apt update
sudo apt install -y \
  python3-pip \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool \
  python3-rosinstall-generator \
  ros-${ROS_DISTRO}-desktop \
  ros-${ROS_DISTRO}-ros2-control \
  ros-${ROS_DISTRO}-ros2-controllers \
  ros-${ROS_DISTRO}-moveit \
  ros-${ROS_DISTRO}-moveit-py \
  ros-${ROS_DISTRO}-moveit-servo \
  ros-${ROS_DISTRO}-gazebo-ros-pkgs \
  ros-${ROS_DISTRO}-gz-ros2-control \
  ros-${ROS_DISTRO}-gz-ros2-control-plugins \
  ros-${ROS_DISTRO}-gz-ros2-control-msgs \
  ros-${ROS_DISTRO}-ros-gz

sudo apt upgrade -y

python3 -m pip install --upgrade pip

sudo rosdep update
rosdep install --from-paths "$SRC_DIR" --ignore-src -r -y

if [ -f "$SRC_DIR/requirements.txt" ]; then
  python3 -m pip install -r "$SRC_DIR/requirements.txt"
fi
if [ -f "$SRC_DIR/cora_common/requirements.txt" ]; then
  python3 -m pip install -r "$SRC_DIR/cora_common/requirements.txt"
fi
if [ -f "$ROOT/requirements.txt" ]; then
  python3 -m pip install -r "$ROOT/requirements.txt"
fi

colcon build --symlink-install

source "/opt/ros/${ROS_DISTRO}/setup.bash"
if ! grep -Fxq "source /opt/ros/${ROS_DISTRO}/setup.bash" "$BASHRC"; then
  echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> "$BASHRC"
fi

if [ -f "$ROOT/install/setup.bash" ]; then
  source "$ROOT/install/setup.bash"
  if ! grep -Fxq "source $ROOT/install/setup.bash" "$BASHRC"; then
    echo "source $ROOT/install/setup.bash" >> "$BASHRC"
  fi
fi

echo "Install complete. Run 'source /opt/ros/${ROS_DISTRO}/setup.bash' and 'source $ROOT/install/setup.bash' to use the workspace."

