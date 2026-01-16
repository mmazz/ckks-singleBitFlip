# Single Bit Flip Campaigns

Both HEAAN and OpenFHE has the same structure.

All the results of the campaigns are in the directory results.
There there is `campaigns.csv` where it has the information of each campaign
runed with an id.
There is a class logger, where its call for each iteration inside the main loop
of bit flip, and internally it buffers the information, and after 10k calls, it
flush it to single campaign csv.
