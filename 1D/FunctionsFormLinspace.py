import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import StepLR
import numpy as np
import matplotlib.pyplot as plt
# from LossRules import 

def F_HO(x):
    """Dynamics for harmonic oscillator"""

    p = x[:,0]
    q = x[:,1]
    F = torch.vstack((-q,p)).T
    return F

def integrate(model,x,b,n,device,rule,F=None):
    """General function for integration of F(model(x,t)) from t=0 to t=b
    using n points and midpoint rule. F is the dynamics.
    """

    #Convert a,b to float
    if type(b) == torch.Tensor:
        if b.size() == 1:
            b = b.cpu().numpy()[0]
        else:
            b = b.cpu().numpy()

    #Set up points
    
    t = torch.linspace(0, b, n+1, dtype=torch.float)[:,None]
    h = t[1]-t[0]
    t = t[:-1] + h/2
    t = t.to(device)

    #Evaluate the model
    ones = torch.ones((n,1), dtype=torch.float).to(device)
    XTensor = ones*x
    if F is None:
        S = model(XTensor,t)
    else:
        S = F(model(XTensor,t))

    #Integrate
    h = torch.tensor(h).to(device)
    AntiDerivative = torch.zeros((len(t),x.shape[1]))

    # for i in range(len(t)-1):

    if rule == 'left_point_rule':
        # print(S[i,:].size(),AntiDerivative[i,:].size(),x.shape[1])
        AntiDerivative[1:] = torch.cumsum(h*S,dim=0)[:-1]
        # AntiDerivative[i+1,:] = AntiDerivative[i,:] + h*S[i,:]

    elif rule == 'right_point_rule':
        # rule_loss += h*torch.sum(S[1:,:],dim=0)
        AntiDerivative[1:] = torch.cumsum(h*S,dim=0)[1:]


    elif rule == 'mid_point_rule':
        # rule_loss += h*torch.sum(S,dim=0)
        # AntiDerivative

    elif rule == 'trapezoid_rule':
    #     rule_loss += (h/2)*(S[0,:] + 2*torch.sum(S[1:-1,:],dim=0) + S[-1,:])
        AntiDerivative[1:] = (torch.cumsum(h*S,dim=0)[:-1] + torch.cumsum(h*S,dim=0)[1:])/2

        # elif rule == 'simpson_rule':
        #     rule_loss += (h/3)*(S[0,:] + 4*torch.sum(S[:-1:2,:],dim=0) + 2*torch.sum(S[1:-1:2,:],dim=0) + S[-1,:])

    return S - XTensor - AntiDerivative

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
        if t.dim()==1:
            t = torch.reshape(t,(len(t),1))
        else:
            t = torch.reshape(t,(len(t),1))
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
model = Net(100).to(device)

#Batch size
batch_size = 1000
epochs = int(1e5)
rule = 'left_point_rule'

#Set up optimizer
optimizer = optim.Adam(model.parameters(), lr=0.01)  #Learning rate
scheduler = StepLR(optimizer, step_size=1, gamma=1)
# gamma=0.001**(1/epochs)



model.train()
#Training epochs
for i in range(epochs):

    #Random initial conditions for p0 and q0
    x = (2*torch.rand(2, dtype=torch.float)-1).to(device)
    x = torch.reshape(x,(1,2))

    #Random final time
    T = 1#*torch.rand(1, dtype=torch.float).to(device)

    #Weak formulation loss
    optimizer.zero_grad()
    # loss_weak = torch.sum((model(x,T) - x - integrate(model,x,T,batch_size,device,rule,F=F_HO))**2)
    loss_weak = torch.mean(torch.abs(integrate(model,x,T,batch_size,device,rule,F=F_HO)))


    #Semigroup loss
    s1 = torch.rand((1,1), dtype=torch.float).to(device) 
    s2 = (1-s1)*torch.rand((1,1), dtype=torch.float).to(device) 
    loss_semigroup = torch.sum((model(x,s1+s2) - model(model(x,s1),s2))**2)
    loss_semigroup += torch.sum((model(x,s1+s2) - model(model(x,s2),s1))**2)

    #Full loss
    loss = loss_weak + loss_semigroup

    #Gradient descent
    loss.backward()
    
    if i == 0  or (i+1)%1000==0:
            print(i,loss.item())

    optimizer.step()
    scheduler.step()


torch.save(model,'semigroup_Function_Linspace.pt')

# device = torch.device('cpu')
# model.to(device)
# t = torch.linspace(0, 1, batch_size, dtype=torch.float)[:,None].to(device)
# ones = torch.ones((batch_size,1), dtype=torch.float).to(device)
# model.eval()
# with torch.no_grad(): #Tell torch to stop keeping track of gradients
#     for i in range(10):
#         plt.figure()
#         x = (2*torch.rand(2, dtype=torch.float)-1).to(device)
#         y = model(ones*x,t)
#         p,q = y[:,0],y[:,1]
#         plt.plot(t, p, label="Neural Net: p")
#         plt.plot(t, q, label="Neural Net: q")

#         p,q = harmonic_oscillator(x[0],x[1],t)
#         plt.plot(t, p, label="Finite Diff: p")
#         plt.plot(t, q, label="Finite Diff: q")

#         plt.legend()
#         plt.savefig('Semigroup_HO_%d.png'%i)
#         plt.close()







