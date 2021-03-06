import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import StepLR
import numpy as np
import matplotlib.pyplot as plt
from time import time

def harmonic_oscillator(p0,q0,t):
    """Finite difference solver for harmonic oscillator"""

    n = len(t)

    p = np.zeros(n)
    q = np.zeros(n)
    p[0],q[0] = p0,q0

    for i in range(1,n):
        h = (t[i]-t[i-1])
        p[i] = p[i-1] - h*q[i-1]
        q[i] = q[i-1] + h*p[i-1]

    return p,q

class Net(nn.Module):
    def __init__(self, n_hidden=100):
        super(Net, self).__init__()
        self.fc1 = nn.Linear(3,n_hidden)
        self.fc2 = nn.Linear(n_hidden,n_hidden)
        self.fc3 = nn.Linear(n_hidden,n_hidden)
        self.fc4 = nn.Linear(n_hidden,2)

    def forward(self, state, t):
        x = torch.hstack((state,t))
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        return x  #(p,q)

if torch.cuda.is_available() == True:
    device = torch.device('cuda')
else: 
    device = torch.device('cpu')

for LearningSize in [1,'T',.9,.8,.7,.6,.5,.4,.3,.2,.1]:

    Start = time()

    print('Start of LearningSize: ' + str(LearningSize))

    model = Net(100).to(device)

    #Set up optimizer
    optimizer = optim.SGD(model.parameters(), lr=0.01)  #Learning rate
    scheduler = StepLR(optimizer, step_size=1, gamma=1)

    #Batch size
    batch_size = 1000
    epochs = int(1e5)

    #Step size
    t = torch.linspace(0, 1, batch_size+1, dtype=torch.float)[:,None]
    h = t[1]-t[0]
    t = t[:-1] + h/2
    t = t.to(device)

    #Ones
    ones = torch.ones((batch_size,1), dtype=torch.float).to(device)

    model.train()
    #Training epochs
    for i in range(epochs):

        #Random initial conditions for p0 and q0
        x = (2*torch.rand(2, dtype=torch.float)-1).to(device)

        #Random final time
        T = torch.rand(1, dtype=torch.float).to(device)

        #Weak formulation loss
        optimizer.zero_grad()
        S = model(ones*x,t*T)

        if LearningSize == 'T':
            loss_weak =  (S[-1,0] - x[0] + T*torch.mean(S[:int(T.numpy()[0]*len(S)),1]))**2  #pt = -q in weak form
            loss_weak += (S[-1,1] - x[1] - T*torch.mean(S[:int(T.numpy()[0]*len(S)),0]))**2  #qt = p in weak form
        elif LearningSize == 1:
            loss_weak =  (S[-1,0] - x[0] + T*torch.mean(S[:,1]))**2  #pt = -q in weak form
            loss_weak += (S[-1,1] - x[1] - T*torch.mean(S[:,0]))**2  #qt = p in weak form
        else:
            loss_weak =  (S[-1,0] - x[0] + T*torch.mean(S[:int(LearningSize*len(S)),1]))**2  #pt = -q in weak form
            loss_weak += (S[-1,1] - x[1] - T*torch.mean(S[:int(LearningSize*len(S)),0]))**2  #qt = p in weak form

        #Semigroup loss
        # s1 = torch.rand((1,1), dtype=torch.float).to(device) 
        # s2 = (1-s1)*torch.rand((1,1), dtype=torch.float).to(device) 
        # x = torch.reshape(x,(1,2))
        # loss_semigroup = torch.sum((model(x,s1+s2) - model(model(x,s1),s2))**2)
        # loss_semigroup += torch.sum((model(x,s1+s2) - model(model(x,s2),s1))**2)

        #Full loss
        loss = loss_weak #+ loss_semigroup

        if torch.isnan(loss).item() == True:
            break

        #Gradient descent
        loss.backward()

        if i == 0 or (i+1)%1000 == 0:
            print(i,loss.item())

        optimizer.step()
        scheduler.step()

    print('End time taken of ' +  str(time() - Start))


    if LearningSize == 1:
        torch.save(model,'no_semigroup_HO.pt')
    else:
        torch.save(model,'no_semigroup_HO' + str(LearningSize).replace(".","") + '.pt')

device = torch.device('cpu')
model.to(device)
t = t.to(device)
ones = ones.to(device)
model.eval()
with torch.no_grad(): #Tell torch to stop keeping track of gradients
    for i in range(10):
        plt.figure()
        x = (2*torch.rand(2, dtype=torch.float)-1).to(device)
        y = model(ones*x,t)
        p,q = y[:,0],y[:,1]
        plt.plot(t, p, label="Neural Net: p")
        plt.plot(t, q, label="Neural Net: q")

        p,q = harmonic_oscillator(x[0],x[1],t)
        plt.plot(t, p, label="Finite Diff: p")
        plt.plot(t, q, label="Finite Diff: q")

        plt.legend()
        plt.savefig('Semigroup_HO_%d.png'%i)
        plt.close()















