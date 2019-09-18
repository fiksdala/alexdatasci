#
# This is a Shiny web application. You can run the application by clicking
# the 'Run App' button above.
#
# Find out more about building applications with Shiny here:
#
#    http://shiny.rstudio.com/
#

library(shiny)
library(lme4)
library(lmerTest)
library(ggplot2)

hads_model <- readRDS('data/hads_model.rds')

# Define UI
ui <- fluidPage(
  # Application Title
  titlePanel(
    "Dissertation Visualization"
  ),
  
  tabsetPanel(
    type='tabs',
    tabPanel(
      'Depression/Anxiety',
      fluidRow(
        column(
          12,
          br(),
          p("    This visualization summarizes the main findings of the Depression/Anxiety portion of my dissertation. I used a multilevel linear growth model to investigate relationships among depression, anxiety, sex, and cortisol reactivity and recovery from acute stress. Some of my friends and family have asked about the main findings of the dissertation, and I think it's often easier to visualize than to read through a dense dissertation. Essentially, I found that anxiety symptoms were associated with blunted responses and flatter recovery slopes, while depression symptoms were associated with an opposite pattern. I examined these effects among both 'responders' (i.e. those who showed a significant cortisol response to the stressor) and 'non-responders' (those who did not). Responses may also appear slightly different between men and women."),
          p('Even typing that out is a lot to take in, which is why I think this visualization is helpful to get some intuition of my findings. This plot shows model-predicted cortisol responses by custom specification. You can easily compare average predicted responses by sex, responders, and level of anxiety and depression. Importantly, since anxiety and depression have basically near-equivalent effects in opposing directions, if you set those symptoms to be the same you will not see a lot of differences in responses. Conversely, effects become more apparent if you have differing levels of depression and anxiety.'),
          p("I don't have a link for my full dissertation quite yet, but if you're interested in these findings you can find a very similar analysis (same data, slightly different approach) in my Psychoneuroendocrinology paper linked below:"),
          uiOutput("pnec_link"),
          p('* Note: SD from mean = "standard deviations away from mean", since I used z-scores in my models.')
        )
      ),
      fluidRow(
        column(
          6,
          h1('Group 1'),
          sliderInput("anx_1", h3("Anxiety (SD from mean)"),
                      min = -3, max = 3, value = 0, step=.1),
          sliderInput("dep_1", h3("Depression (SD from mean)"),
                      min = -3, max = 3, value = 0, step=.1),
          fluidRow(
            column(3,
                   radioButtons("sex_1", h3("Sex"),
                                choices = list("Male" = 'Male', 
                                               "Female" = 'Female'),
                                selected = 'Male')),
            column(3,
                   radioButtons("resp_1", h3("Responder"),
                                choices = list("Responder" = 0, 
                                               "Non-Responder" = 1),
                                selected = 0)))
        ),
        
        column(
          6,
          h1('Group 2'),
          sliderInput("anx_2", h3("Anxiety (SD from mean)"),
                      min = -3, max = 3, value = 0, step=.1),
          sliderInput("dep_2", h3("Depression (SD from mean)"),
                      min = -3, max = 3, value = 0, step=.1),
          fluidRow(
            column(3,
                   radioButtons("sex_2", h3("Sex"),
                                choices = list("Male" = 'Male', 
                                               "Female" = 'Female'),
                                selected = 'Female')),
            column(3,
                   radioButtons("resp_2", h3("Responder"),
                                choices = list("Responder" = 0, 
                                               "Non-Responder" = 1),
                                selected = 0)))
        )
      ),
      fluidRow(
        column(10,
               plotOutput('curve'),
               align='center')
      )
      
    )
  )
)

# Define server logic
server <- function(input, output) {
  
  pnec_url <- a("Psychoneuroendocrinology Paper", 
                href="https://www.ncbi.nlm.nih.gov/pubmed/30513499")
  output$pnec_link <- renderUI({
    tagList("", pnec_url)
  })
  
  new_df <- reactive({
    new_df = data.frame(
      React=rep(c(-3,0,0),2),
      Recov=rep(c(0,0,4),2),
      Sex=c(rep(input$sex_1, 3), rep(input$sex_2, 3)),
      zAge=rep(0,6),
      zBMI=rep(0,6),
      Time=rep(c(-30,0,40),2),
      Study=rep('Study_1',6),
      zhads_a=c(rep(input$anx_1, 3), rep(input$anx_2, 3)),
      zhads_d=c(rep(input$dep_1, 3), rep(input$dep_2, 3)),
      NonResp=c(rep(input$resp_1==1, 3), rep(input$resp_2==1, 3)),
      Group=factor(c(1,1,1,2,2,2))
    )
    new_df
  })
  
  output$curve <- renderPlot({
    ggplot(cbind(new_df(),cort=predict(hads_model, 
                                       new_df(),
                                       re.form=NA)), 
           aes(Time,cort,color=Group)) +
      geom_line() +
      theme_bw() +
      scale_x_continuous(name='Time (from peak)',
                         breaks=seq(-30,40,10)) +
      scale_y_continuous(name='Cortisol (log nmol/l)') + 
      theme(aspect.ratio = 1) +
      ggtitle('Estimated (log) Cortisol Response by Custom Specification') +
      theme(plot.title = element_text(hjust = 0.5))
  })
}

# Run the application 
shinyApp(ui = ui, server = server)

