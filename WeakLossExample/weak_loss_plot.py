"""Weak Loss for Solving ODEs with Neural Networks"""
import torch.optim as optim
from torch.optim.lr_scheduler import StepLR
import numpy as np
import torch.nn as nn
import torch.nn.functional as func
import matplotlib.pyplot as plt
import torch

#Our neural network as 2 layers with 100 hidden nodes 
class Net(nn.Module):
    def __init__(self, n_hidden=100):
        super(Net, self).__init__()
        self.fc1 = nn.Linear(1,n_hidden)
        self.fc2 = nn.Linear(n_hidden,n_hidden)
        self.fc3 = nn.Linear(n_hidden,1)

    def forward(self, x):
        x = func.relu(self.fc1(x))
        x = func.relu(self.fc2(x))
        x = self.fc3(x)
        return x

#Use double precision everywhere
torch.set_default_dtype(torch.float64)

#Batch size
T = np.pi #final time
batch_size = 1000
dx = T/batch_size
epochs = 100000
x = torch.arange(dx,T+dx,dx).reshape((batch_size,1))
phi = 1 - torch.exp(-x)
x_mid = x - dx/2
phi_mid = 1 - torch.exp(-x_mid)

model=torch.load('weak_loss_model.pt',map_location=torch.device('cpu'))

model.eval()
#Plot solution
with torch.no_grad(): #Tell torch to stop keeping track of gradients
    net = (phi*model(x)).numpy()
    true = torch.sin(x).numpy()
    x = x.numpy()

    plt.figure()
    plt.plot(x,net,label='Neural Net')
    plt.plot(x,true,label='True Solution')
    plt.legend()
    plt.savefig('NeuralNetPlot.pdf')

    plt.figure()
    plt.plot(x,np.absolute(net-true))
    plt.title('Error')
    plt.savefig('NeuralNetErrorPlot.pdf')

plt.show()
