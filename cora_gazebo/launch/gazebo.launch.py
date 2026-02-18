"""

launch:
ros2 launch cora_gazebo gazebo.launch.py gazebo_world:=../chess/gazebo/worlds/chess_world.sdf

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


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)

    try:
        with open(absolute_file_path, "r") as file:
            return yaml.safe_load(file)
    except (
        EnvironmentError
    ):  # parent of IOError, OSError *and* WindowsError where available
        return None

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
            # " gripper_package:=",
            # gripper_package,
        ]
    )

    robot_description = {"robot_description": robot_description_content}

    #################
    # Moveit Config #
    #################

    # Build configs WITHOUT calling robot_description() yet
    builder = MoveItConfigsBuilder(robot_name="cora", package_name="cora_moveit_config")
    builder.trajectory_execution(file_path="config/moveit_controllers.yaml")
    builder.moveit_cpp(
        file_path=get_package_share_directory("cora_moveit")
        + "/config/cora_moveit.yaml"
    )

    # Override robot_description so it uses runtime Command(...)
    builder.robot_description = lambda: robot_description

    moveit_config = builder.to_moveit_configs()

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

    ####################
    # Launch arguments #
    ####################

    world_arg = DeclareLaunchArgument(
        "gazebo_world",
        description="Path to the Gazebo world file to load",
        default_value="None",
    )
    arguments = [world_arg]

    ########################
    # Launch Configuration #
    ########################
    gazebo_world = LaunchConfiguration("gazebo_world", default="None")

    #########
    # Nodes #
    #########

    # Rviz config
    rviz_config_file = os.path.join(
        get_package_share_directory("cora_moveit_config"),
        "config",
        "moveit.rviz",
    )

    # Rviz node
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        parameters=[
            robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
        ],
    )

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
        ],
    )

    # Static Transforms
    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_transform_publisher",
        output="log",
        arguments=["--frame-id", "world", "--child-frame-id", "base_link"],
    )

    # Ros 2 controllers config
    ros2_controllers_path = os.path.join(
        get_package_share_directory("cora_moveit_config"),
        "config",
        "ros2_controllers.yaml",
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
    )

    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller',
                   '--param-file',
                   ros2_controllers_path,
                   ],
    )

    # Robot State Publisher
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="log",
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
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"
        ],
    )

    # Robot Spawner
    robot_spawner_node = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name",
            "cora",
            "-topic",
            "robot_description",
            "-allow_renaming",
            "true",
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

    nodes = [robot_state_publisher, robot_spawner_node, world_spawner_node, bridge]

    ########################
    # Launch file Includes #
    ########################

    # # Bringup launch file
    # bringup_launch = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(bringup_launch_dir),
    #     launch_arguments={
    #         "use_codi": "true",
    #         "hardware_type": "Gazebo",
    #         "launch_rsp": "false",
    #         # "gripper_package": "cora_gripper_1_description"
    #     }.items(),
    # )

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
            "debug": "true"
        }.items(),
    )

    launch_files = [
        gazebo_launch,
    ]

    #############################
    # Event handlers and timers #
    #############################

    spawner_event_handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=robot_spawner_node,
            on_exit=[joint_state_broadcaster_spawner],
        )
    )

    spawner_event_handler_2 = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[arm_controller_spawner],
        )
    )

    spawner_event_handler_3 = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=arm_controller_spawner,
            on_exit=[gazebo_launch],
        )
    )

    event_handlers = [spawner_event_handler, spawner_event_handler_2]

    return LaunchDescription(
        launch_files
        + nodes
        + arguments
        + event_handlers
    )
