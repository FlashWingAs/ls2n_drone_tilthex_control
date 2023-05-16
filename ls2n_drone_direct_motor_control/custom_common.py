import numpy as np
from enum import IntEnum
from ls2n_interfaces.msg import DroneStatus
from ls2n_interfaces.srv import DroneRequest
from rclpy.qos import qos_profile_sensor_data

class Custom_Pose:
    time = 0.0
    position = np.array([0.0, 0.0, 0.0])                                            # 3D-vector of position
    velocity = np.array([0.0, 0.0, 0.0])                                            # 3D-vector of velocity
    acceleration = np.array([0.0, 0.0, 0.0])                                        # 3D-vector of acceleration

    rotation = np.array([0.0, 0.0, 0.0, 0.0])                                       # (x,y,z,w) quaternion of orientation
    rot_velocity = np.array([0.0, 0.0, 0.0])                                        # 3D-vector of instantaneous rotation speed
    rot_acceleration = np.array([0.0, 0.0, 0.0])                                    # 3D-vector of instantaneous rotation acceleration
    rotation_matrix = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]) # 3-by-3 rotation matrix of the drone in the world reference

class Custom_Controller_Type(IntEnum):
    NONE = (0,)
    TEST = (1,)
    GEOMETRIC = 2

def wedge_op(A):
    a1 = A[2, 1]
    a2 = A[0, 2]
    a3 = A[1, 0]
    a_x = np.array([a1, a2, a3])
    return(a_x)