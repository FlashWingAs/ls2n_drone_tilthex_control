import numpy as np
from scipy.spatial.transform import Rotation as R
import transforms3d as tf3d
from geometry_msgs.msg import Vector3Stamped
from ls2n_interfaces.msg import MotorControlSetPoint

from ls2n_drone_direct_motor_control.custom_common import Custom_Pose, Custom_Controller_Type

class Custom_Controller:

    def __init__(self, node):
        self.node = node
    
    type = Custom_Controller_Type.NONE
    desired_pose = Custom_Pose()

    def update_trajectory_setpoint(self, msg):
        if 1:
            self.desired_pose.position = np.array([0.0, 0.0, 2.0]) #fixed set point of 2m altitude
        else:
            for index, coordinate in enumerate(msg.joint_names):
                position = 0.0
                velocity = 0.0
                acceleration = 0.0
                if len(msg.points[0].positions) > index:
                    position = msg.points[0].positions[index]
                if len(msg.points[0].velocities) > index:
                    velocity = msg.points[0].velocities[index]
                if len(msg.points[0].accelerations) > index:
                    acceleration = msg.points[0].accelerations[index]
                if coordinate == "x":
                    self.desired_state.position[0] = position
                    self.desired_state.velocity[0] = velocity
                    self.desired_state.acceleration[0] = acceleration
                elif coordinate == "y":
                    self.desired_state.position[1] = position
                    self.desired_state.velocity[1] = velocity
                    self.desired_state.acceleration[1] = acceleration
                elif coordinate == "z":
                    self.desired_state.position[2] = position
                    self.desired_state.velocity[2] = velocity
                    self.desired_state.acceleration[2] = acceleration
                if coordinate == "phi":
                    self.desired_state.rotation[0] = position
                    self.desired_state.rot_velocity[0] = velocity
                    self.desired_state.rot_acceleration[0] = acceleration
                elif coordinate == "theta":
                    self.desired_state.rotation[1] = position
                    self.desired_state.rot_velocity[1] = velocity
                    self.desired_state.rot_acceleration[1] = acceleration
                elif coordinate == "psi":
                    self.desired_state.rotation[2] = position
                    self.desired_state.rot_velocity[2] = velocity
                    self.desired_state.rot_acceleration[2] = acceleration
                elif coordinate == "R11" :
                    self.desired_pose.rotation_matrix[0, 0] = position
                    self.desired_pose.rotation_matrix_derivative[0, 0] = velocity
                elif coordinate == "R12" :
                    self.desired_pose.rotation_matrix[0, 1] = position
                    self.desired_pose.rotation_matrix_derivative[0, 1] = velocity
                elif coordinate == "R13" :
                    self.desired_pose.rotation_matrix[0, 2] = position
                    self.desired_pose.rotation_matrix_derivative[0, 2] = velocity
                elif coordinate == "R21" :
                    self.desired_pose.rotation_matrix[1, 0] = position
                    self.desired_pose.rotation_matrix_derivative[1, 0] = velocity
                elif coordinate == "R22" :
                    self.desired_pose.rotation_matrix[1, 1] = position
                    self.desired_pose.rotation_matrix_derivative[1, 1] = velocity
                elif coordinate == "R23" :
                    self.desired_pose.rotation_matrix[1, 2] = position
                    self.desired_pose.rotation_matrix_derivative[1, 2] = velocity
                elif coordinate == "R31" :
                    self.desired_pose.rotation_matrix[2, 0] = position
                    self.desired_pose.rotation_matrix_derivative[2, 0] = velocity
                elif coordinate == "R32" :
                    self.desired_pose.rotation_matrix[2, 1] = position
                    self.desired_pose.rotation_matrix_derivative[2, 1] = velocity
                elif coordinate == "R33" :
                    self.desired_pose.rotation_matrix[2, 2] = position
                    self.desired_pose.rotation_matrix_derivative[2, 2] = velocity
                else:
                    self.node.get_logger.warn(
                        "Invalid coordinate" + coordinate + " received."
                    )

    def do_control(self, _):
        pass

class Test_Controller(Custom_Controller):
    def __init__(self, node):
        super().__init__(node)
        self.type = Custom_Controller_Type.TEST

    def init_controller(self):
        pass

    def do_control(self):
        desired_motor_speed = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        return desired_motor_speed
    
    def debug_controller_desired_pose(self):
        return self.desired_pose

class Geometric_Controller(Custom_Controller):

    def __init__(self, node):
        super().__init__(node)
        self.type = Custom_Controller_Type.GEOMETRIC
    
    # Geometry
    pi = np.pi
    Lx = 0.686/2
    alpha = pi/3
    g = 9.81
    m_tot = 3.3981
    I1 = 0.1
    I2 = I1
    I3 = 0.15
    I = np.diag(np.array([I1, I2, I3]))
    I_inv = np.linalg.pinv(I)
    lambda_arms = np.array([-pi/2, pi/2, pi/6, -5*pi/6, -pi/6, 5*pi/6])
    alpha_arms = alpha*np.array([-1, 1, -1, 1, 1, -1])
    clock = np.array([1, -1, 1, -1, -1, 1]) # Clockwise or Anti-clockwise

    # Force and drag coefficient of the propeller -> replaced by computing control thrust-wise and using d as kd/kt
    # kf = 0.002
    # kd = 0.0002
    d = 0.06

    # PID coef
    k_p_pos = 29*I3 #10.0
    k_i_pos = 30*I3 #0.5
    k_d_pos = 10*I3 #0.0001
    k_p_ang = k_p_pos #0.01
    k_i_ang = k_i_pos #0.001
    k_d_ang = k_d_pos #0.0
    standard_geometric_controller_parameters = [k_p_pos, k_i_pos, k_d_pos, k_p_ang, k_i_ang, k_d_ang]
    Kpp = np.eye(3)
    Kpi = np.eye(3)
    Kpd = np.eye(3)
    Krp = np.eye(3)
    Kri = np.eye(3)
    Krd = np.eye(3)

    # Errors init
    e_pos_old = np.zeros((3,1))
    e_pos = np.zeros((3,1))
    D_e_pos = np.zeros((3,1))
    I_e_pos = np.zeros((3,1))

    e_ang_old = np.zeros((3,1))
    e_ang = np.zeros((3,1))
    D_e_ang = np.zeros((3,1))
    I_e_ang = np.zeros((3,1))
    
    # Mixer init
    B_P_Pi = np.zeros((6,3,1))
    B_R_Pi = np.zeros((6,3,3))
    F = np.zeros((3,6))
    H = np.zeros((3,6))

    # Calc f

    f = np.array([[0], [0], [-g*m_tot], [0], [0], [0]])

    # Calc Jb

    for i in range(6):
        temp_lambda = R.from_euler('ZYX', np.array([lambda_arms[i], 0, 0])).as_matrix()
        temp_alpha = R.from_euler('ZYX', np.array([0, 0, alpha_arms[i]])).as_matrix()
        B_P_Pi[i, :, :] = np.matmul(temp_lambda, np.transpose([np.array([Lx, 0, 0])]))
        B_R_Pi[i, :, :] = np.matmul(temp_lambda, temp_alpha)
        F[:, [i]] = np.matmul(np.reshape(B_R_Pi[[i], :, :], (3, 3)), 
                                    np.transpose([np.array([0, 0, 1])]))
        H[:, [i]] = np.cross(np.reshape(B_P_Pi[[i], :, :], (3, 1)),
                                    np.transpose(np.matmul(np.reshape(B_R_Pi[[i], :, :], (3, 3)), np.transpose(np.array([0, 0, 1])))),
                                    axis=0) + np.reshape(clock[i]*np.matmul(np.reshape(B_R_Pi[[i], :, :], (3, 3)),
                                                        np.transpose(np.array([0, 0, d]))),(3,1))

    Jb = np.concatenate((F, H), axis=0)

    def init_controller(self, parameters= standard_geometric_controller_parameters):
        self.Kpp = parameters[0]*np.eye(3)
        self.Kpi = parameters[1]*np.eye(3)
        self.Kpd = parameters[2]*np.eye(3)
        self.Krp = parameters[3]*np.eye(3)
        self.Kri = parameters[4]*np.eye(3)
        self.Krd = parameters[5]*np.eye(3)

    def do_control(self, real_pose : Custom_Pose, step_size : float, do_trajectory : bool):
        if not do_trajectory:
            self.desired_pose = Custom_Pose()
            self.desired_pose.position = np.array([0.0, 0.0, 1.5]) #fixed set point of 1.5m altitude

        # updates

        # self.D_e_pos = (np.reshape(self.desired_pose.position, (3, 1)) - self.e_pos)/step_size
        # self.I_e_pos = self.I_e_pos + np.reshape(self.desired_pose.position, (3, 1))*step_size
        # self.e_pos_old = self.e_pos
        # self.e_pos = np.reshape(real_pose.position, (3, 1)) - np.reshape(self.desired_pose.position, (3, 1))

        
        self.e_pos_old = self.e_pos
        self.e_pos = np.reshape(real_pose.position, (3, 1)) - np.reshape(self.desired_pose.position, (3, 1))
        self.I_e_pos = self.I_e_pos + self.e_pos*step_size
        self.D_e_pos = (self.e_pos-self.e_pos_old)/step_size
  
        self.e_ang_old = self.e_ang
        e_ang = 1/2*np.reshape(R.from_matrix(np.matmul(np.transpose(self.desired_pose.rotation_matrix), real_pose.rotation_matrix) - \
                                              np.matmul(np.transpose(real_pose.rotation_matrix), self.desired_pose.rotation_matrix)).as_rotvec(), (3, 1))
        self.I_e_ang = self.I_e_ang + e_ang*step_size
        self.D_e_ang = np.reshape(real_pose.rot_velocity, (3, 1)) - \
            np.matmul(np.matmul(np.transpose(real_pose.rotation_matrix), self.desired_pose.rotation_matrix),
                      np.reshape(R.from_matrix(np.matmul(np.transpose(self.desired_pose.rotation_matrix),
                                                               self.desired_pose.rotation_matrix_derivative)).as_rotvec(), (3, 1)))
        


        # Calc V

        DD_p_d = np.reshape(self.desired_pose.acceleration, (3, 1))
        DD_r_d = np.reshape(self.desired_pose.rot_acceleration, (3, 1))

        Vp = DD_p_d - np.matmul(self.Kpd, self.D_e_pos) - np.matmul(self.Kpp, self.e_pos) - np.matmul(self.Kpi, self.I_e_pos)
        Vr = DD_r_d - np.matmul(self.Krd, self.D_e_ang) - np.matmul(self.Krp, self.e_ang) - np.matmul(self.Kri, self.I_e_ang)
        v = np.concatenate((Vp, Vr), axis=0)

        # Calc J

        JR = np.concatenate((np.concatenate((real_pose.rotation_matrix/self.m_tot, np.zeros((3, 3))), axis=0),
                             np.concatenate((np.zeros((3, 3)), self.I_inv), axis=0)),
                             axis=1)
        J = np.matmul(JR, self.Jb)

        # Calcl u

        J_inv = np.linalg.inv(J)

        u = np.matmul(J_inv, (-self.f+v))
        for i in range(6):
            if u[i]<0:
                u[i] = 0
        desired_motor_thrust = u

        return desired_motor_thrust
    
    def debug_controller_desired_pose(self):
        return self.desired_pose