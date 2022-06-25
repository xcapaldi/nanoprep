#!/usr/bin/env python3

# Nanopore Conditioning - Quick Plot
# AUTHOR: Xavier Capaldi
# DATE: 2021-05-31

# import necessary packages
import sys
import csv
import matplotlib.pyplot as plt

# this will allow dragging and dropping csv's to plot on Windows
file = sys.argv[1]

# setup arrays
time = []
voltage = []
current = []

# open csv
with open(file, newline='') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        # ignore protocol details
        if row[0][0] != '#' and row[0][0] != 'T':
            time.append(float(row[0]))
            voltage.append(float(row[1]))
            current.append(float(row[2]) * 10E9)

# plot
plt.plot(time, current, '-', label='data')
plt.xlabel('time (s)')
plt.ylabel('current (nA)')
plt.legend()
plt.show()
