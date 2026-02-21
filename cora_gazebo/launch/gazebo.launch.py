"""

launch:
ros2 launch cora_gazebo gazebo.launch.py gazebo_world:=../chess/gazebo/worlds/world_2/chess_world.sdf

"""

import os
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import (
    IncludeLaunchDescription,
    RegisterEventHandler,
    DeclareLaunchArgument,
    AppendEnvironmentVariable,
    ExecuteProcess,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.conditions import IfCondition
from launch.event_handlers import (
    OnExecutionComplete,
)
import os
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():

    ##############
    # File Paths #
    ##############

    # Cora bringup launch file path
    bringup_launch_dir = os.path.join(
        get_package_share_directory("cora_bringup"), "launch", "bringup.launch.py"
    )

    # Gazebo world file path
    main_world = os.path.join(
        get_package_share_directory("cora_gazebo"), "worlds", "main_world.sdf"
    )

    # Gazebo resource path for cora meshes
    gazebo_models_path = os.path.join(
        get_package_share_directory("cora_description"), "meshes"
    )

    # Gazebo resource path for cora gripper meshes
    gazebo_gripper_path = os.path.join(
        get_package_share_directory("cora_gripper_1_description"), "meshes"
    )
    ########################
    # Launch Configuration #
    ########################

    gazebo_world = LaunchConfiguration("gazebo_world", default="None")
    hardware_type = LaunchConfiguration("hardware_type", default="Gazebo")
    gripper_package = LaunchConfiguration("gripper_package", default="cora_gripper_1_description")

    #####################
    # Robot Description #
    #####################

    robot_description_content = Command(
        [
            "xacro ",
            PathJoinSubstitution(
                [FindPackageShare("cora_moveit_config"), "config", "cora.urdf.xacro"]
            ),
            " hardware_type:=",
            "Gazebo",
            " gripper_package:=",
            gripper_package,
        ]
    )

    robot_description = {"robot_description": robot_description_content}

    #########################
    # Command Substitutions #
    #########################

    # GZ resources
    models = AppendEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=gazebo_models_path,
    )
    gripper_models = AppendEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=gazebo_gripper_path,
    )

    get_height = ExecuteProcess(
        cmd=[
            "bash", "-c",
            "gz topic -e -t /world/main_world/scene/info | grep robot_link -A 20"
        ],
        output="screen"
    )

    ####################
    # Launch arguments #
    ####################

    declared_arguments = []

    declared_arguments.append(
        DeclareLaunchArgument(
            "gazebo_world",
            description="Path to the Gazebo world file to load",
            default_value="None",
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            "gripper_package",
            description="Path to the Gazebo world file to load",
            default_value="cora_gripper_1_description",
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            "hardware_type",
            description="Path to the Gazebo world file to load",
            default_value="Gazebo",
        )
    )


    #########
    # Nodes #
    #########

    # Robot State Publisher
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    # Bridge
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        arguments=[
            "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model",
            "/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        ],
    )

    # Robot Spawner
    robot_spawner_node = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name", "cora",
            "-topic", "robot_description",
            "-allow_renaming", "true",
            "-x", "0.0",
            "-y", "0.4",
            "-z", "0.82",
            "-R", "0.0",
            "-P", "0.0",
            "-Y", "-1.570796326",
        ],
        output="screen",
    )

    # World model spawner
    world_spawner_node = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-name", "main_world", "-file", gazebo_world],
        output="screen",
    )

    nodes = [robot_state_publisher, robot_spawner_node, world_spawner_node]

    ########################
    # Launch file Includes #
    ########################

    # Bringup launch file
    bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(bringup_launch_dir),
        launch_arguments={
            "use_codi": "true",
            "hardware_type": "Gazebo",
            "launch_rsp": "false",
            "use_sim_time": "true",
            "gripper_package": "cora_gripper_1_description"
        }.items(),
    )

    # Gazebo sim
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py"
            )
        ),
        launch_arguments={
            "gz_args": f"-r {main_world} --verbose 4",
            "on_exit_shutdown": "true",
            "debug": "true",
        }.items(),
    )

    # Bridge
    ros_gz_bridge_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("ros_gz_bridge"), 
                "launch", 
                "ros_gz_bridge.launch.py"
            )
        ),
        launch_arguments={
            "bridge_name": "ros_gz_bridge",
            "config_file": os.path.join(
                get_package_share_directory("cora_gazebo"),
                "config",
                "ros_gz_bridge.yaml"
            ),
            # "use_composition": "True",
            # "create_own_container": "True"
        }.items(),
    )

    launch_files = [
        gazebo_launch,
        ros_gz_bridge_launch,
    ]

    #############################
    # Event handlers and timers #
    #############################

    bringup_spawner_event_handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=robot_spawner_node,
            on_exit=[bringup_launch],
        )
    )

    event_handlers = [bringup_spawner_event_handler]

    return LaunchDescription(launch_files + nodes + declared_arguments + event_handlers)
