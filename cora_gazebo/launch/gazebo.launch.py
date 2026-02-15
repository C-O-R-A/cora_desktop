'''

launch:
ros2 launch cora_gazebo gazebo.launch.py gazebo_world:=../chess/gazebo/worlds/chess_world.sdf

'''
import os
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import (
    IncludeLaunchDescription,
    RegisterEventHandler,
    DeclareLaunchArgument,
    AppendEnvironmentVariable

)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch.conditions import IfCondition
from launch.event_handlers import (
    OnExecutionComplete,
)
import os

def generate_launch_description():

    ##############
    # File Paths #
    ##############

    # Cora bringup launch file path
    bringup_launch_dir = os.path.join(
        get_package_share_directory("cora_bringup"), 
        "launch", 
        "bringup.launch.py"
    )

    # Gazebo world file path
    main_world = os.path.join(
        get_package_share_directory("cora_gazebo"),
        "worlds",
        "main_world.sdf"
    )

    # Gazebo resource path for cora meshes
    gazebo_models_path = os.path.join(
        get_package_share_directory("cora_description"),
        "meshes"
    )

    # Gazebo resource path for cora gripper meshes
    gazebo_gripper_path = os.path.join( 
        get_package_share_directory("cora_gripper_1_description"), 
        "meshes" 
    )

    #########################
    # Command Substitutions #
    #########################
    
    # GZ resources
    models = AppendEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=gazebo_models_path,
    )
    gripper_models = AppendEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=gazebo_gripper_path,
    )

    ####################
    # Launch arguments #
    ####################

    world_arg = DeclareLaunchArgument(
        "gazebo_world",
        description="Path to the Gazebo world file to load",
        default_value='None'
    )
    arguments = [world_arg]

    ########################
    # Launch Configuration #
    ########################
    gazebo_world = LaunchConfiguration("gazebo_world", default="None")

    #########
    # Nodes #
    #########
    # Bridge
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        arguments=[
            "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model",
            "/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"
        ]
    )

    # Robot Spawner
    robot_spawner_node = Node(
                            package='ros_gz_sim',
                            executable='create',
                            arguments=[
                                '-name', 'cora',
                                '-topic', 'robot_description',
                                '-allow_renaming', 'true'
                            ],
                            output='screen',
                        )
    
    # World model spawner
    world_spawner_node = Node(
                            package='ros_gz_sim',
                            executable='create',
                            arguments=[
                                '-name', 'main_world',
                                '-file', gazebo_world
                            ],
                            output='screen'
    )
    
    nodes = [robot_spawner_node, world_spawner_node, bridge]

    ########################
    # Launch file Includes #
    ########################

    # Bringup launch file
    bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            bringup_launch_dir
        ),
        launch_arguments={
            "use_codi": "true",
            "hardware_type": "Gazebo",
            # "gripper_package": "cora_gripper_1_description"
        }.items(),
    )

    # Gazebo sim
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("ros_gz_sim"), 
                "launch", 
                "gz_sim.launch.py"
            )
        ),
        launch_arguments={
            "gz_args": f"-r {main_world} --verbose 4",
            "on_exit_shutdown": "true"
        }.items(),
    )

    # # Bridge
    # ros_gz_bridge_launch = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         os.path.join(
    #             get_package_share_directory("ros_gz_bridge"), 
    #             "launch", 
    #             "ros_gz_bridge.launch.py"
    #         )
    #     ),
    #     launch_arguments={
    #         "bridge_name": "ros_gz_bridge",
    #         "config_file": os.path.join(
    #             get_package_share_directory("cora_gazebo"),
    #             "config",
    #             "ros_gz_bridge.yaml"
    #         ),
    #         "use_composition": "True",
    #         "create_own_container": "True"
    #     }.items(),
    # )


    launch_files = [bringup_launch, 
                    gazebo_launch, 
                    # ros_gz_bridge_launch
                    ]
    
    #############################
    # Event handlers and timers #
    #############################

    spawner_event_handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=robot_spawner_node,
            on_exit=[bringup_launch],
        )
    )

    event_handlers = [spawner_event_handler]

    return LaunchDescription(
        launch_files
        + nodes
        + arguments
        # + event_handlers
    )
