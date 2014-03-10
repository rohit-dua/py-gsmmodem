import sys, time, serial
import Queue, re, threading


phone = serial.Serial(0, 460800, timeout=1)         # open first serial port
print phone.portstr          # check which port was really used
recipient = "xxxxxxxxxx"
message = "Here, therde\r\n\r\nOK\r\nfake"
send_sms_LOCK = threading.Lock()
phone_write_LOCK = threading.Lock()
phone_write_verify_LOCK = threading.Lock()
Event_recv_sms = threading.Event()
Event_recv_response = threading.Event()
Event_del_sim_sms = threading.Event()

class QUEUE:
  response = Queue.Queue(10)          # //check usefulness (if any)
  sms = Queue.Queue(10)
  call = Queue.Queue(10)
  sim_sms_index = Queue.Queue(10)
  
class global_var:
  del_sim_sms_index = int


def disconnect():
  phone.close()

  
def phone_write(data):
  phone_write_LOCK.acquire()          # phone_write_LOCK Acquired
  phone.write(data)
  phone_write_LOCK.release()          # phone_write_LOCK Released


def phone_write_verify(data,valid = ""):
  print "phone_write_verify started"
  phone_write_verify_LOCK.acquire()         # phone_write_verify_LOCK Acquired
  return_value = 1
  phone_write(data)
  Event_recv_response.wait()
  Event_recv_response.clear()
  response = QUEUE.response.get()         # Pop item from Queue:response
  if valid == "":
    return_value = response
  else:
    if re.match(valid,response) is None:
      return_value = response
  phone_write_verify_LOCK.release()         # phone_write_verify_LOCK Released
  return return_value
  
  
def reset_modem():
  phone_write_verify('AT&F\r', "OK\r\n")
  phone_write_verify('AT&W\r', "OK\r\n")
  time.sleep(2)
  phone_write('\n\r')
  
  
def send_sms(recipient,message):
  print "send_sms started"
  send_sms_LOCK.acquire()          # send_sms_Lock Acquired
  #print "send_sms started"+recipient+phone.portstr
  status = phone_write_verify('AT+CMGF=1\r', 'OK\r\n')
  status = phone_write_verify('AT+CMGS="' + recipient + '"\r', "> ")
  status = phone_write_verify(message + chr(26), "\r\n"+r"\+CMGS: [\d]+"+"\r\n\r\nOK\r\n")
  #disconnect()
  print "Exiting send_sms"
  send_sms_LOCK.release()         # send_sms_Lock Released
  return 1
  
  
def delete_sim_sms():
  while True:
    Event_del_sim_sms.wait()
    Event_del_sim_sms.clear()
    while QUEUE.sim_sms_index.empty() is False:
      status = phone_write_verify('AT+CMGD='+QUEUE.sim_sms_index.get()+'\r', 'OK\r\n')          # SMS index no. taken from sim_sms_index QUEUE           
  return 1


def receive_sms():
  print "receive_sms started"
  while(True):
    Event_recv_sms.wait()
    Event_recv_sms.clear()
    while QUEUE.sms.empty() is False:         # Response in sms QUEUE
      msg_raw = QUEUE.sms.get()         # Response taken from sms QUEUE
      print "msg_raw:"+msg_raw
      index = re.search(r'\+CMTI: "\w\w",([\d]+)'+'\r\n',msg_raw)
      index = index.group(1)
      QUEUE.sim_sms_index.put(index)          # SMS index no. written to sim_sms_index QUEUE
      Event_del_sim_sms.set() 
      status = phone_write_verify('AT+CMGF=1\r', 'OK\r\n')
      status = phone_write_verify('AT+CSDH=1\r', 'OK\r\n')
      msg_buffer = phone_write_verify('AT+CMGR='+index+'\r')
      #print "Message Receied:\n"+msg
      msg=re.search(r'\+CMGR: "[\s\w]*","([\+\d\w-]*)","?([\w\d-]*)"?,"([\d/]+),([\d:]+)\+[\d]+",[\d]+,([\d]+),[\S ]*' + '(?s)\r\n(.+)',msg_buffer)
      print "msg: >>"+msg_buffer+"<<"
      msg_length = int(msg.group(5))
      print "\nFrom: "+msg.group(1)+"("+msg.group(2)+")" \
            "\nDate: "+msg.group(3)+ \
            "\nTime: "+msg.group(4)+ \
            "\nMessage: "+msg.group(6)[:msg_length-1]
  return 1
   
   
def receive_data():
  print "receive_data started"
  buf = []
  token = 0
  buf_temp = ['','']
  while(True):
    token_rec_newline = 0
    buf_temp[0] = phone.readline()
    if buf_temp[0] == "":
      continue
    if buf_temp[0] == '\r\n':
      buf_temp[1] = phone.readline()
      if re.match(r'\+CMTI: "\w\w",[\d]+'+'\r\n',buf_temp[1]) is not None:
        QUEUE.sms.put(buf_temp[1])          # Response to receive_msg()
        Event_recv_sms.set()
        continue
      if buf_temp[1] == 'RING\r\n' or buf_temp[1] == 'NO CARRIER\r\n':
        QUEUE.call.put(buf_temp[1])         # Response to receive_call()
        continue
      if token ==1:
        buf.append(buf_temp[0])
        buf.append(buf_temp[1])
        buf_temp[0]=buf_temp[1]
        token_rec_newline = 1
    if token == 1:
      if token_rec_newline == 0:
        buf.append(buf_temp[0])
      if buf_temp[0] == '> ':
        QUEUE.response.put(buf_temp[0])            # Response to send_msg
        Event_recv_response.set()
        token = 0
        continue
      if buf_temp[0] == 'OK\r\n' or (re.search('ERROR',buf_temp[0]) is not None):
        token = 0
        buf = ''.join(buf)
        QUEUE.response.put(buf)           # Response to send_msg/send_ussd/get_contacts/receive_call etc.
        Event_recv_response.set()
        buf=[]
      continue
    if buf_temp[0] != '\r\n' and token == 0:
      token = 1
      continue  
  return 1


    
  
  
def main():

  #try:
    """
    reset_modem()
    sent_status=send_sms(recipient,message)
    if sents_status == 1:
      print "Message Successfully Sent to "+recipient
    """
    #send_sms(recipient,message)
    #receive_sms()
    #phone_write("AT+CMGR=2\r")
    #buf=[]
    #while(True):
    #  buf.append(phone.readline())
    """
    t1 = threading.Thread(target = send_sms, args = (recipient,message))
    t1.start()
    #receive_sms()
    """
    
    #reset_modem()
    
    #thread_send_sms = threading.Thread(target = send_sms, args = (recipient,message))
    #thread_send_sms.start()
    
    thread_delete_sim_sms = threading.Thread(target = delete_sim_sms)
    thread_delete_sim_sms.start()
    
    thread_receive_data = threading.Thread(target = receive_data)
    thread_receive_data.start()
    
    thread_receive_sms = threading.Thread(target = receive_sms)
    thread_receive_sms.start()
    
    
    
    print "Exiting Main() without Error"
    
  #except:
    #disconnect()
    #print "Exiting Main() with error"



if __name__ == '__main__':
  main()  
