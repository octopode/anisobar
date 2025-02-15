#!/usr/bin/python3

file_data = "20200714_t-log.tsv"

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import itertools
import pandas as pd

# Create figure for plotting
fig = plt.figure()
ax1 = fig.add_subplot(3, 1, 1)
ax2 = fig.add_subplot(3, 1, 2)
ax3 = fig.add_subplot(3, 1, 3)
t = []
temp_ext = []
temp_int = []
temp_set = []
Cp = []
Ci = []
Cd = []
Hp = []
Hi = []
Hd = []

# This function is called periodically from FuncAnimation
def animate(i, t, temp_ext, temp_int, temp_set, Cp, Ci, Cd, Hp, Hi, Hd):
    
    data = pd.read_csv(file_data, sep='\t')

    t = data['watch']
    temp_ext = data['T_ext']
    temp_int = data['T_int']
    temp_set = data['T_set']
    Cp = data['Cp']
    Ci = data['Ci']
    Cd = data['Cd']
    Hp = data['Hp']
    Hi = data['Hi']
    Hd = data['Hd']

    # Draw x and y lists
    ax1.clear()
    ax1.plot(t, temp_ext, c="red")
    ax1.plot(t, temp_int, c="green")
    ax1.plot(t, temp_set, c="yellow")
    
    plt.ylabel('Temperature (deg C)')
    
    # Draw x and y lists
    ax2.clear()
    ax2.plot(t, Cp, c="darkblue")
    ax2.plot(t, Ci, c="lightblue")
    ax2.plot(t, Cd, c="blue")
    
    plt.ylabel('parameter value')
    
    # Draw x and y lists
    ax3.clear()
    ax3.plot(t, Hp, c="darkred")
    ax3.plot(t, Hi, c="pink")
    ax3.plot(t, Hd, c="red")
    
    plt.ylabel('parameter value') 

    # Format plot
    #plt.xticks(rotation=45, ha='right')
    #plt.subplots_adjust(bottom=0.30)
    #plt.title('TMP102 Temperature over Time')
    plt.xlabel('time (s)')
    

# Set up plot to call animate() function periodically
ani = animation.FuncAnimation(fig, animate, fargs=(t, temp_ext, temp_int, temp_set, Cp, Ci, Cd, Hp, Hi, Hd), interval=1000)
plt.show()

#def my_animate(ax, i, file_data, colors, x, **kwargs):
#    "The above, but with series passed as kwargs, x-axis name as x"
#    
#    data = pd.read_csv(file_data, sep='\t')
#    
#    # load data series from file
#    kwargs = {key: data[key] for key, val in kwargs}
#    
#    ax.clear()
#    # for every kwarg except the x-axis
#    for key, val in {k: v for k, v in kwargs if k != x}.items():
#        ax.plot(kwargs[x], val)
#
#class dashboard:
#   "Class for an arbitrarily defined set of live plots"
#   def __init__(self, axs, coords, file_data):
#       """
#       axs is a list of previously defined axes;
#       coords is a list of lists of dicts containing kwargs to Ax.plot()
#       """
#       self.fig = plt.figure()
#       self.axs = axs
#       self.coords = coords
#       self.file_data = file_data
#       
#       # init lists
#       for colname in list(itertools.chain.from_iterable(coords)):
#           eval("self.{} = []".format(colname))
#   
#   def animate(self, **kwargs):
#       
#       # load data from file
#       data = pd.read_csv(self.file_data, sep='\t')
#       # load data series from file
#       kwargs = {key: data[key] for key, val in kwargs}
#       
#       # loop thru axes
#       for ax, dataset in zip(self.axs, self.coords):
#           ax.clear()
#           for series in dataset:
#               ax.plot(**series)
#          
#   def run(self)
#   