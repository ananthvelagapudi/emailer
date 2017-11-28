from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os, sys, smtplib, shutil, pickle, multiprocessing
from multiprocessing import Queue,Lock, Process
import time



def sendMultiPartMail(filename, responseq):
    ERROR = 0
    CONNECTED = False
    RECONNECT_DELAY_SECONDS = 5
    # Unpickle the data file and get the data within the file.
    with open(filename, 'rb') as f:
        tple = pickle.load(f)

    #Extract data from the data file.
    #ID of the server. This is an internal reference related to the program, not to the smtp server.
    serverid = tple[0]

    # SMTP Server Address . Ex : smtp.office365.com
    smtpserveraddress = tple[1]

    # SMTP Port Number.
    smtpport = tple[2]

    # SMTP Username
    smtpusername = tple[3]
    
    # SMTP Password
    smtppassword = tple[4]

    # List of Email addresses to which the emails are to be sent.
    emails = tple[5]

    # Subject of the emails.
    subject = tple[6]

    # Content of the emails.
    content = tple[7]

    # Program related setting that specifies how many emails to be sent per second.
    MAILS_PER_MINUTE = tple[8]

    # Program related setting that specifies the minimum time difference between emails in seconds
    DELAY_BETWEEN_MAILS = tple[9]

    strmsg = "SMTP Server : " + str(serverid) + " started."
    responseq.put("MESSAGE#*#"+str(serverid)+"#*#"+strmsg)

    try:
        responseq.put(str("MESSAGE#*#"+str(serverid)+"#*#"+"Trying to Connect to SMTP Server.."+ str(smtpserveraddress)+ "-"+ str(smtpusername)))
        smtpsrv = smtplib.SMTP(smtpserveraddress, smtpport)
        smtpsrv.ehlo()
        smtpsrv.starttls()
        smtpsrv.ehlo()
        smtpsrv.login(smtpusername,smtppassword)
        responseq.put(str("MESSAGE#*#"+str(serverid)+"#*#"+"Login Successful"+ str(smtpserveraddress)+ "-"+ str(smtpusername)))
        CONNECTED = True
    except:
        ERROR = 1
        CONNECTED = False
        responseq.put(str("ERROR#*#"+str(serverid)+"#*#"+"Unexpected error:"+str(sys.exc_info()[0])))
    # Sends one email to the specified recipient.
    if(CONNECTED):
        responseq.put(str("MESSAGE#*#"+str(serverid)+"#*#"+"Starting sending of emails from server : "+str(serverid)))
        process_start_time = time.time()
        timepermail = 60/MAILS_PER_MINUTE
        presenttime = 0
        timediff = 0
        if ( len(emails) > 0 and ERROR != 1 ) :
            for em in emails:
                msg = MIMEMultipart('alternative')
                msg['From'] = smtpusername
                msg['Subject'] = subject
                msg['To'] = em
                p1 = MIMEText(content, 'text')
                p2 = MIMEText(content, 'html')
                msg.attach(p1)
                msg.attach(p2)
                try:
                    presenttime = time.time()
                    smtpsrv.sendmail(smtpusername, em, msg.as_string())
                    responseq.put("MESSAGE#*#"+str(serverid)+"#*#"+"Email sent to :"+str(em)+" From server : "+str(serverid))
                    responseq.put("EMAIL-SUCCESS#*#"+str(serverid)+"#*#"+str(em))
                    timediff = time.time() - presenttime
                    if(timediff < timepermail):
                        time.sleep(timepermail-timediff)
                    time.sleep(DELAY_BETWEEN_MAILS)
                    timediff = 0
                    presenttime = 0
                except (smtplib.SMTPServerDisconnected):
                    CONNECTED = False
                    while not CONNECTED:
                        time.sleep(RECONNECT_DELAY_SECONDS)
                        try:
                            responseq.put(str("MESSAGE#*#"+str(serverid)+"#*#"+"Trying to Connect to SMTP Server.."+ str(smtpserveraddress)+ "-"+ str(smtpusername)))
                            smtpsrv = smtplib.SMTP(smtpserveraddress, smtpport)
                            smtpsrv.ehlo()
                            smtpsrv.starttls()
                            smtpsrv.ehlo()
                            smtpsrv.login(smtpusername,smtppassword)
                            responseq.put(str("MESSAGE#*#"+str(serverid)+"#*#"+"Login Successful"+ str(smtpserveraddress)+ "-"+ str(smtpusername)))
                            CONNECTED = True
                        except:
                            ERROR = 1
                            CONNECTED = False
                            responseq.put(str("ERROR#*#"+str(serverid)+"#*#"+"Unexpected error:"+str(sys.exc_info()[0])))
                except:
                    responseq.put(str("ERROR#*#"+str(serverid)+"#*#"+"Unexpected error:"+str(sys.exc_info()[0])))
            smtpsrv.quit()
        responseq.put(str("QUIT#*#"+str(serverid)+"#*#"+"Completed !!"))
    return True
