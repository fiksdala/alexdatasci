srate = 256;
time = -2:1/srate:2;
frex = 5;

sine_wave = exp(1i*2*pi*frex.*time);

s = 7/(2*pi*frex);
gaus_win = exp( (-time.^2) ./ (2*s^2) ) ;

cmw = sine_wave .* gaus_win;


exp((-time.^2)./(2*s^2));