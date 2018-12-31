
"""
/* Link Telemetry v2.0 "Mobile"

   Copyright (c) 2015-2017 University of Maryland Space Systems Lab
   NearSpace Balloon Payload Program

   Written by Nicholas Rossomando
   2015-04-11

   Permission is hereby granted, free of charge, to any person obtaining a copy
   of this software and associated documentation files (the "Software"), to deal
   in the Software without restriction, including without limitation the rights
   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   copies of the Software, and to permit persons to whom the Software is
   furnished to do so, subject to the following conditions:

   The above copyright notice and this permission notice shall be included in all
   copies or substantial portions of the Software.

   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
   SOFTWARE.

   GroundTrack.py:

   Declares ground track container & handler class. Takes over derived quantity
   calculation from Packet itself; also does a whole lot more quantities. Also
   separates out ground tracks from different callsigns.
*/
"""
import PacketClass
import 'Output/LogClass'

class GroundTrack():

    """
    Sets up the GroundTrack class with all vars and initial conditions.
    """

    def __init__(self):
        logEnabled = False
        jsonEnabled = False
        kmlEnabled = False
        ascentRate = 0
        groundSpeed = 0
        downrangeDist = 0
        timeToImpact = -5
        latlonDerrivative = [0,0,0]
        latestCallsign = [['', '', ''], []]

    def calculateAscentRate(self):
        """
        Calculate ascent rate function.
        Simple difference right now.
        Will look into filtering very, very soon.
        (Need to make it work before I make it better.)
        Emits result in ft/s; conversion to m/s in print function.
        If ascent rate is negative (descent rate), also estimate time to sea level impact.
        """

        calcPackets = getLatest(2)  # Gets the 2 most recent packets
        deltaAltitude = calcPackets[0].getPacket().alt - calcPackets[1].getPackets().alt  # Calc diff in alt in ft
        deltaTime = diffTime(calcPackets)  # Get time between packets

        if deltaTime != 0:
            ascentRate = deltaAltitude/deltaTime

    def calculateAscentRate(self):
        """
        Ground speed calculation function.
        Simple difference - won't be filtered.
        Filter here would change GPS provided coords,
        And I honestly don't want to do that.
        This isn't really that critical anyway.
        Emits result in mph; conversion to m/s in print function.
        """

        calcPackets = getLatest(2)  # Gets the 2 most recent packets
        distanceTraveled = diffLatLon(calcPackets)  # Get ground distance between packets
        deltaTime = diffTime(calcPackets)  # Get time between packets

        if deltaTime != 0:
            hours = deltaTime/3600  # Converts from seconds to hours
            groundSpeed = distanceTraveled/hours  # Calc speed in MPH



def list_search(n, my_list=None):
    """
    Search for the specified number in a given list.

    Assume the input list is sorted in ascending order, but not necessarily 
    consecutive. Integers may be repeated. Shoot for an expected runtime of 
    log(n) for full credit.


    Parameters
    ----------
    n : int
        the specific element to search for 

    my_list : list(int)
        list of elements to search through


    Returns
    -------
    int 
        the element's index within the list or -1 if the element is not present
    """
    
    if my_list is None:
        my_list = []
        list_size = 1000
        int_range = 10000
        for _ in range(list_size):
            elem = random.randint(-int_range/2, int_range/2)
            my_list.append(elem)
            my_list.sort()

    # replace the line below with your implementation

    #2a)
    # Jump to halfway though the list and check if x is more or less than that value. If it is less go to halfway through the bottom half.
    #If it is greater than that value jump to the halway point of the upper half. If it equals the value stop. repeat until x is found
    # Generate a random list if no list is specified

    #2c) O(log(n))
    run=0
    index=-1
    high=len(my_list)-1
    mid=int(len(my_list)/2)
    low=0
    while(high-mid>=0):
        if(my_list[mid]==n):
            index=mid
            mid=high+1000
        elif(my_list[mid]<n):
            low=mid
            mid=int((high-low)/2)+low+1
        elif(my_list[mid]>n):
            high=mid-1    
            mid=int((high-low)/2)+low
    #Time complexity:
    #Sum from i=1 to log_2_(n) of 3
    # O(3*log_2_(n))
    print(index)
    return index
list_search(4, my_list=[1,2,3,5,6,7])

class Ball:
    def __init__(self, mass=10):
        self.x = 0
        self.y = 0
        self.mass = mass


def curve_balls(t, n):
    """
    Propagate the random movement and splitting of balls over time.

    Assume the input list is sorted in ascending order, but not necessarily 
    consecutive. Integers may be repeated. Shoot for an expected runtime of 
    log(n) for full credit.


    Parameters
    ----------
    t : int
        the number of time steps to propagate the algorithm

    n : int
        number of balls to initially start with
       
    """

    # initialize list of balls
    balls = []
    for i in range(n):
        balls.append(Ball())

    # propagate balls through each timestep
    for _ in range(t):
        balls_generated = []
        for b in balls:
            curve_ball(b)
            ball_new = split_ball(b)
            balls_generated.append(ball_new)
        balls += balls_generated    # append all newly generated balls to the list of balls
        # Time complexity: 
        # Sum from 1 to t of the sum from 1 to n of 17. All added to 2t. 
        # O(17nt+2t)


def curve_ball(ball):
    """
    Assigns a random value between -1 and 1 to the x and y coordinates of a ball. 


    Parameters
    ----------
    ball : Ball
        Ball with positon (x,y) and a mass m
        
    Returns
    -------
    None
       
    """

    ball.x += random.uniform(-1,1)
    ball.y += random.uniform(-1,1)
    
    if ball.x > 10:
        ball.x = 10
    elif ball.x < -10:
        ball.x = -10

    if ball.y > 10:
        ball.y = 10
    elif ball.y < -10:
        ball.y = -10


def split_ball(ball_og):
    """
    Takes in an original ball, and then duplicates it and cuts the mass in half. 

    
    Parameters
    ----------
    ball_og : Ball
        The original ball
    
    Returns
    -------
    ball_new : Ball
        A new ball, with the position as the original ball and half the mass of the original ball


    """
    ball_og.mass /= 2
    ball_new = Ball(mass=ball_og.mass)
    ball_new.x = ball_og.x
    ball_new.y = ball_og.y
    return ball_new




