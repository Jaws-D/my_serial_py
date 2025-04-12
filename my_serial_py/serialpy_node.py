import rclpy
from rclpy.node import Node
from referee_msg.msg import Referee
from geometry_msgs.msg import Twist
import serial
import json
import struct
import threading
import time

class SerialNode(Node):
    def __init__(self):
        super().__init__('serial_node')

        self.serial_port = '/dev/ttyUSB0'
        self.baud_rate = 115200
        self.get_logger().info(f'Serial port set to: {self.serial_port}')

        try:
            self.serial_conn = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            self.get_logger().info(f'Connected to {self.serial_port} at {self.baud_rate} baud.')
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to open serial port: {e}')
            rclpy.shutdown()
            return

        self.last_cmd_vel = Twist()
        self.subscription = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.publisher_ = self.create_publisher(Referee, 'stm32_ros2_data', 10)

        # 启动独立线程
        threading.Thread(target=self.read_serial_thread, daemon=True).start()
        threading.Thread(target=self.send_serial_thread, daemon=True).start()

    def cmd_vel_callback(self, msg):
        self.last_cmd_vel = msg

    def send_serial_thread(self):
        while rclpy.ok():
            try:
                header = 0xAA
                checksum = 19
                x_speed = self.last_cmd_vel.linear.x
                y_speed = self.last_cmd_vel.linear.y
                rotate = self.last_cmd_vel.angular.z
                yaw_speed = self.last_cmd_vel.angular.z
                running_state = 0x01

                data_frame = struct.pack('<BBffffB',
                    header, checksum, x_speed, y_speed, rotate, yaw_speed, running_state
                )

                if self.serial_conn.is_open:
                    self.serial_conn.write(data_frame)

            except serial.SerialException as e:
                self.get_logger().error(f'Serial send error: {e}')
            time.sleep(0.02)  # 50Hz

    def read_serial_thread(self):
        while rclpy.ok():
            try:
                if self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        try:
                            parsed = json.loads(line)
                            self.publish_referee_msg(parsed)
                        except json.JSONDecodeError as e:
                            self.get_logger().warn(f'JSON parse error: {e}')
            except serial.SerialException as e:
                self.get_logger().error(f'Serial read error: {e}')
            time.sleep(0.01)  # roughly 100Hz max

    def publish_referee_msg(self, data):
        msg = Referee()
        msg.game_type = int(data.get('game_type', 0))
        msg.game_progress = int(data.get('game_progress', 0))
        msg.remain_hp = int(data.get('remain_hp', 0))
        msg.max_hp = int(data.get('max_hp', 0))
        msg.stage_remain_time = int(data.get('stage_remain_time', 0))
        msg.bullet_remaining_num_17mm = int(data.get('bullet_remaining_num_17mm', 0))
        msg.red_outpost_hp = int(data.get('red_outpost_hp', 0))
        msg.red_base_hp = int(data.get('red_base_hp', 0))
        msg.blue_outpost_hp = int(data.get('blue_outpost_hp', 0))
        msg.blue_base_hp = int(data.get('blue_base_hp', 0))
        msg.rfid_status = int(data.get('rfid_status', 0))
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = SerialNode()
    try:
        rclpy.spin(node)  # 只负责处理 ROS 回调（cmd_vel）
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
