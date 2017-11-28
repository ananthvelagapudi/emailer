import os, sys, smtplib, shutil, pickle, multiprocessing
from multiprocessing import Queue,Lock, Process
import time
from mailbox import sendMultiPartMail


# The main function.
def main():
    # Default values for settings, later updated after being read from a file.
    MAILS_PER_MINUTE = 30
    DELAY_BETWEEN_MAILS = 0.01
    DATA_DIR = os.path.join(os.getcwd(),'data') #".\data"
    subject = "Some Subject"

    sentemails = []

    # Get the SMTP list.
    filename = "smtp.txt"
    curdir = os.getcwd()
    filepath = os.path.join(curdir, filename)
    smtpservers = []
    f = open(filepath)
    serverid = 0
    for line in f:
        ln = line.strip().split(' ')
        smtpservers.append((serverid, ln[0], ln[1], ln[2], ln[3]))
        serverid += 1
    f.close()

    # Get the body of the mail.
    content  = ""
    filename = "content.txt"
    filepath = os.path.join(curdir, filename)
    f = open(filepath)
    for line in f:
        content+=line
    f.close()

    # Get the email list
    emails = []
    filename = "emails.txt"
    filepath = os.path.join(curdir, filename)
    f = open(filepath)
    for line in f:
        emails.append(line.strip())
    f.close()

    # Clear the existing sentmails file
    filename = "sentemails.txt"
    sentmailfilepath = os.path.join(curdir, filename)
    with open(sentmailfilepath, 'r+') as file_handler:
        file_handler.seek(0)
        # This will clear the contents of the file.
        file_handler.truncate()

    # Get the settings.
    settings = []
    filename = "settings.txt"
    filepath = os.path.join(curdir, filename)
    f=open(filepath)
    for line in f:
        settings = line.strip().split(sep='=')
        if settings[0] == 'MAILS_PER_MINUTE':
            MAILS_PER_MINUTE = int(settings[1])
        if settings[0] == 'DELAY_BETWEEN_MAILS' :
            DELAY_BETWEEN_MAILS = float(settings[1])
        if settings[0] == 'SUBJECT' :
            subject = settings[1]
    print("MAILS_PER_MINUTE : ",MAILS_PER_MINUTE)
    print("DELAY_BETWEEN_MAILS : ",DELAY_BETWEEN_MAILS)
    print("Subject is : ",subject)

    # Clean up the SMTP Servers
    preparedservers = []
    print("Checking server authentication")
    for server in smtpservers:
        # Login to the servers to find out whether the server auth is working.
        print("Validating SMTP server authentication for SMTP SERVER :", server[1],
            ":", server[2], "Username/Password : ", server[3], "/", server[4])
        smtpsrv = object()
        try:
            smtpsrv = smtplib.SMTP(server[1], server[2])
            smtpsrv.ehlo()
            smtpsrv.starttls()
            smtpsrv.ehlo()
            smtpsrv.login(server[3], server[4])
            tple = object()
            tple = (server[0], server[1], server[2], server[3], server[4])
            preparedservers.append(tple)
        except smtplib.SMTPHeloError:
            print(server[1],'//',server[2], '//',server[3],' : ','ERROR ',smtplib.SMTPHeloError)
        except smtplib.SMTPAuthenticationError:
            print(server[1], '//', server[2], '//', server[3], ' : ', 'ERROR ', smtplib.SMTPAuthenticationError)
        except smtplib.SMTPNotSupportedError:
            print(server[1], '//', server[2], '//', server[3], ' : ', 'ERROR ', smtplib.SMTPNotSupportedError)
        except smtplib.SMTPException:
            print(server[1], '//', server[2], '//', server[3], ' : ', 'ERROR ', smtplib.SMTPException)
        except:
            print("Unexpected error:", sys.exc_info()[0])

    
    # Calculations to determine how many emails are to be allocated to each server.
    nServers = len(preparedservers)
    nEmails = len(emails)
    nEmailsPerServer = 1
    if nEmails > nServers and nServers>0:
        modu = nEmails % nServers
        nEmailsPerServer = int((nEmails - modu) / nServers)

    emailset = []
    for i in range(nServers-1):
        emailset.append(emails[0:nEmailsPerServer])
        emails[0:nEmailsPerServer] = []
    emailset.append(emails)

    queue_map={}
    process_map = {}
    processess = []

    # Distribute the workload.
    emailsetindex = 0
    if len(preparedservers) > 0:
        print("Creating Data Files")
        for server in preparedservers:
            server = (*server, emailset[emailsetindex], subject, content, MAILS_PER_MINUTE,DELAY_BETWEEN_MAILS)
            fname = os.path.join(DATA_DIR,str(server[0])+".dat")
            print(fname)
            with open(fname,'wb') as f:
                pickle.dump(server,f)
            q = Queue()
            queue_map.update({server[0]:q})
            p = Process(target=sendMultiPartMail,args=(fname,q))
            p.start() # Start the processing immediately.
            print("Thread for server:",server[0]," started. Awaiting results")
            processess.append(p)
            process_map.update({server[0]:p})
            emailsetindex+=1
        

        while(len(queue_map)>0):
            poplist = []
            for key in queue_map:
                qu = queue_map[key]
                msg=""
                try:
                    msg = qu.get(block = False)
                except:
                    pass
                if msg != "":
                    msg = msg.split('#*#')
                    if(msg[0] == 'QUIT'):
                        poplist.append(msg[1])
                    elif(msg[0] == 'EMAIL-SUCCESS'):
                        sentemails.append(msg[2])
                        if(len(sentemails>50)):
                            print("Saving data to :",sentmailfilepath)
                            with open(sentmailfilepath, 'a') as file_handler:
                                for item in sentemails:
                                    file_handler.write("{}\n".format(item))
                                del sentemails[:]
                    else:
                        print(msg[2])
            for item in poplist:
                queue_map.pop(int(item))
                process_map[int(item)].join()
                print("Thread operating with server",item," Closed")
                    
    if len(sentemails) > 0:
        with open(sentmailfilepath, 'a') as file_handler:
            for item in sentemails:
                file_handler.write("{}\n".format(item))
    print("Hooray !! Completed !!")




if __name__ == '__main__':    
    main()