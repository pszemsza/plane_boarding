# Plane boarding methods, or in search of time lost

We all know how annoyingly inefficient boarding a plane is. We can't do anything about it, but we can try to measure exactly how inefficient it is.

Here we assume a 16 rows, 3-seats-a-side plane (bigger planes often have multiple sections of that approximate size, with separate entrances). We also assume constant time for moving (2 units of time for moving by 1 row), stowing baggage (3 units of time) and seating (3 units of time per seat). For each setting a simulation was run 1000 times and the mean time was calculated.

First, lets jump straight to the results - the distribution of boarding times for the (selected) methods described below is presented below:


![plot](https://github.com/pszemsza/plane_boarding/assets/65168262/0d5bec19-4c5a-419f-aee8-fa8612fecf5d)

## How to use
This repo contains the following files:
* plane_boarding.py - simulation library
* main.py - runs the simulations
* animate.py - Processing.py sketch used to create animations shown below


## Boarding methods

Let's start with the most obvious boarding scheme: back to front, with 2 and 3 zones.


https://github.com/pszemsza/plane_boarding/assets/65168262/7a02d51c-b662-4b91-8524-3788dedbb20d


https://github.com/pszemsza/plane_boarding/assets/65168262/007e2465-bbcc-4318-a38f-57f55ea2a8b4


Interestingly, boarding time is larger with 3 zones than with 2. The intuition behind this might be seen by pushing the number of zones to the maximum, with every row being a separate zone:


https://github.com/pszemsza/plane_boarding/assets/65168262/84aca3b9-e0f7-4fd9-b599-0eac27bcc58b


Here the problem is clear - people in a given row can only seat if all the people in the following rows already moved past it. But as there are 2*3=6 people per row, which all need to stow their baggage, a long queue is quickly formed, with at most 2 people stowing baggage at the same time (in 2 consecutive rows). The situation is not that bad e.g. for 2 zones, but there is still a problem - for anyone in zone 2 to seat almost all of the passengers from zone 1 need to move past it and/or be seated. With the time of boarding increasing with more and more zones one might wonder - wouldn't it be faster to have just a single zone (or, in other words, not have any zones at all)? As it turns out, it would be, by 7%!


https://github.com/pszemsza/plane_boarding/assets/65168262/281f82f3-f9af-48ff-b16f-e264ff6e0c60


Now the obvious question arises - can we do better than no zones? An obvious optimization would be to seat people in the window-to-aisle order, which would remove the need of passengers vacating the rows to let someone seating closer to the window through. Let's see:


https://github.com/pszemsza/plane_boarding/assets/65168262/dc4ce1a0-388e-497d-ba24-5ba670467ccd


Woah, a 24% improvement! Can we do better still? A highly orchestrated boarding method was suggested by [Steffen](https://en.wikipedia.org/wiki/Steffen_Boarding_Method).


https://github.com/pszemsza/plane_boarding/assets/65168262/c6347151-4f33-409e-81ad-2828d4ec9ed6


This gives us 46% improvement over the random boarding. To see if we can optimize this further, we can observe that the only waiting time in Steffen method is when a new batch of passengers arrives, and must wait for the last passenger from a previous batch (which always seat in row 1 or 2). To limit this waiting time, we can pack passengers more densely, so that in every batch there is exactly one passenger per row, again in a window-to-aisle order.


https://github.com/pszemsza/plane_boarding/assets/65168262/d63662be-8473-4fbb-8a84-a110bde9aa04


This gives us a 56% improvment over the random method, and we can be easily see that it can't be further improved upon. While being much faster, the last 2 methods have little practical use - they use as many boarding zones as there are seats on the plane. It might look like a heaven on the plane, but it would truly be a hell trying to organize all the people to queue correctly before the gate! Another practial disadvantage is that it would split people travelling together (and sitting next to each other). To accomodate for that, Steffen suggested a modified version, with only 4 zones: odd rows on the right, odd rows on the left, followed by even rows on the right and on the left.


https://github.com/pszemsza/plane_boarding/assets/65168262/a3c42656-1392-41e5-9069-1931be38f2ca


This method doesn't work very well in our setting, and is a mere 1% faster than the random boarding. If we can live with numerous zones, and only care about families boarding together, then we can board by rows, leaving 2 row gaps between zones, in the back-to-front order. This leaves a space for the passengers sitting in different rows not to interfere with each others.


https://github.com/pszemsza/plane_boarding/assets/65168262/8f0fe222-e310-4d07-b244-a27b191d48d9


This gives a decent 29% improvement over the random, but requires twice as many zones as there are rows, so is not very practical.

As we have seen, boarding back to front by rows is very inefficient. The good news is, it could be even worse! Boarding front to back would take more than twice as long as boarding using a random method:


https://github.com/pszemsza/plane_boarding/assets/65168262/46aff98c-a0e1-4c43-adc2-aeea9dd9fb10




