from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    rm_serial = Node(
        package="my_serial_py",
        executable="serial_node",
        name="serial",
        output='screen',
    )
    return LaunchDescription(
        [
            rm_serial
        ]
    )