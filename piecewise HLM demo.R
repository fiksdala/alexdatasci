################################################################################
# Piecewise HLM demo
# 
# This outlines a piecewise hierarchical linear model, with one increase slope,
# one decrease slope, and a single level 2 predictor. This data is entirely
# simulated, is not representative of anything and is only for illustration
# purposes. Briefly, data should be in long format, with intercepts representing
# peaks. Increase and decrease slopes are level 1 predictors, with individual
# observations nested within subjects. Increase/decrease predictors should
# be included as random slopes whenever there is significant between-subjects
# variation. anova() likelihood ratio testing should be used to determine
# differences in level 2 residuals. lmerTest uses satterwaith df adjustemnts
# by default. 
#
# I highly recommend reading the documentation for lme4:
# https://cran.r-project.org/web/packages/lme4/lme4.pdf
# 
# This is only a basic demo. This sort of model may not be appropriate in 
# all situations. Consult with a statistician regarding specific hypothesis
# testing and how to best set up an analytic plan for your needs. 
# Be sure your data meet all assumptions required for HLM.
################################################################################

# Make some simulated/fake data

## Make varying baselines, slopes, peaks, and add noise
## Add influence of fake_predictor (fp)
make_curve = function(fpv=0){
  # Random Peak
  peak_time = sample(c(30,40,50,60),
                1,
                replace=TRUE,
                prob = c(.3,.4,.2,.1))
  # Random baseline
  b = rnorm(1,10,1)
  # Random increase
  a_inc = runif(1,.05,.15)
  x_inc = seq(0,peak_time,10)
  
  # Random decrease
  a_dec = runif(1,-.1,-.025)
  x_dec = seq(10,(13-length(x_inc))*10,10)
  peak = b+max(x_inc)*a_inc
  
  # Add influence of fake predictor
  a_inc = a_inc + fpv
  a_dec = a_dec - fpv
  
  # Make the curve
  curve = c(b+x_inc*a_inc,
            peak+x_dec*a_dec)
  
  # Add noise
  curve = curve + runif(13,0,2.5)
  
  # Return curve and peak_time
  list(curve=curve,peak=peak_time)
}


## Make dataset with ID, time, time_c, increase, decrease, fake predictor, dv
### Make fake predictor mean coefficient
fpc = .01 # fake predictor coefficient
fpc_sd = .001 # fake predictor sd
fake_data = data.frame()
# Make 300 fake observations
for(subject in 1:300){
  fp = rnorm(1,0,1) # Fake predictor value (z-score)
  loop_fpv = rnorm(1,fpc,fpc_sd)*fp # Add noise to fake predictor
  loop_curve = make_curve(loop_fpv) # Get curve and peak time values
  
  # Get time vars
  time=seq(0,120,10)
  time_c = time-loop_curve$peak # peak-centered time
  increase = ifelse(time_c<0,time_c,0)
  decrease = ifelse(time_c>0,time_c,0)
  
  fake_data = rbind(fake_data,
                    data.frame(id=rep(subject,13),
                               time=time,
                               time_c = time_c,
                               increase = increase,
                               decrease = decrease,
                               fp = rep(fp,13),
                               dv = loop_curve$curve
                               )
                    )
}

# Look at fake data
head(fake_data,39)

# NOTE: time_c (peak-centered time) is 0 when increase and decrease are both 0. 
# This represents the peak/intercept.
# NOTE: increase is 0 during decrease, and decrease is 0 during increase
# DATA MUST BE ORGANIZED IN THIS MANNER FOR THIS TYPE OF MODEL TO WORK

# Look at curves, note different peaks and slopes
library(ggplot2)
ggplot(fake_data,aes(time,dv,color=factor(id))) +
  geom_line() + 
  scale_color_manual(values=rep('gray',300)) +
  theme(legend.position = 'none') + 
  stat_summary(fun.y=mean, geom="line", colour="black")

# NOTE: With time scaled as it is now, sometimes the model will not converge.
# In order to avoid that (and make it run faster), I will rescale
# increase and decrease variables 1/10--i.e., units will represent 10 minute
# intervals instead of 1 minute intervals. If model doesn't fail to converge, 
# you don't need to rescale (though rescaling will make it run faster)
# If you do rescale, remember that will change interpretation of coefficients.
# Example of rescale: decrease_rs and increase_rs represent 10 min intervals
fake_data$decrease_rs = fake_data$decrease/10
fake_data$increase_rs = fake_data$increase/10

# Make a piecewise growth model with increase and decrease:
library(lme4)
library(lmerTest)

# No random slopes:
m0 = lmer(dv ~ increase_rs + decrease_rs
          + (1|id),
          data=fake_data)
summary(m0)

# Check if slopes vary by ID
m1 = lmer(dv ~ increase_rs + decrease_rs
          + (increase_rs + decrease_rs|id),
          data=fake_data)
summary(m1)
anova(m0,m1) # Significant likelihood ratio test, keep random slopes.

# Now run model with fake predictor, level 1
m2 = lmer(dv ~ (increase_rs + decrease_rs)+fp
          + (increase_rs + decrease_rs|id),
          data=fake_data)
summary(m2)
anova(m1,m2) # Fake predictor alone does not predict dv

# Now test fp X increaese and fp X decrease interactions simultaneously
m3 = lmer(dv ~ (increase_rs + decrease_rs)*fp
          + (increase_rs + decrease_rs|id),
          data=fake_data)
summary(m3) # Some significant coefficients
anova(m2,m3) # Significant likelihood ratio test

# Don't forget to inspect residuals
plot(m3)