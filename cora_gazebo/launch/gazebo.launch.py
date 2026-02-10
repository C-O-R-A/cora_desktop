'''

launch:
ros2 launch cora_gazebo gazebo.launch.py gazebo_world:=../chess/gazebo/worlds/chess_world.sdf

'''
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import (
    IncludeLaunchDescription,
    RegisterEventHandler,
    DeclareLaunchArgument,
    TimerAction,
)
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

    main_world = os.path.join(
        get_package_share_directory("cora_gazebo"),
        "worlds",
        "main_world.sdf"
    )

    ####################
    # Launch arguments #
    ####################

    world_arg = DeclareLaunchArgument(
        "gazebo_world",
        description="Path to the Gazebo world file to load",
    )
    arguments = [world_arg]

    ########################
    # Launch Configuration #
    ########################
    gazebo_world = LaunchConfiguration("gazebo_world", default="None")

    #########
    # Nodes #
    #########

    # Robot Spawner
    robot_spawner_node = Node(
                            package='ros_gz_sim',
                            executable='create',
                            parameters=[{
                                'name': 'cora',
                                'topic': 'robot_description'
                            }],
                            output='screen',
                        )
    
    # World model spawner
    world_spawner_node = Node(
                            package='ros_gz_sim',
                            executable='create',
                            parameters=[{
                                'name': 'main_world',
                                'file': gazebo_world
                            }]
    )
    
    nodes = [robot_spawner_node, world_spawner_node]

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
            "hardware": "Fake",
            "gripper_package": "cora_gripper_1_description"
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
            "gz_args": f"-r {main_world}",
            "on_exit_shutdown": "true"
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
            "use_composition": "True",
            "create_own_container": "True"
        }.items(),
    )

    launch_files = [bringup_launch, 
                    gazebo_launch, 
                    ros_gz_bridge_launch]

    return LaunchDescription(
        launch_files
        + nodes
        + arguments
    )
