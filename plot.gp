
set terminal png size 8192,4096
set output 'accel.png'
set title 'Acceleration over Time'
set xlabel 'Time (s)'
set ylabel 'Acceleration (m/s²)'
set grid
plot 'accel.dat' using 1:2 with lines title 'X',      'accel.dat' using 1:3 with lines title 'Y',      'accel.dat' using 1:4 with lines title 'Z'
