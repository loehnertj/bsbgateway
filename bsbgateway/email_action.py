import logging
log = lambda: logging.getLogger(__name__)
import smtplib
from email.mime.text import MIMEText
from threading import Thread

from bsb.bsb_fields import fields

def make_email_action(server, address, credentials):
    def send_async(msg):
        log().info('About to send email notification "%s"'%msg['Subject'])
        s = smtplib.SMTP_SSL(server)
        s.login(*credentials)
        s.sendmail(address, [address], msg.as_string())
        s.quit()
        log().info('Email was sent.')
        
    def callback(logger, triggertype, param1, param2, prev_val, this_val):
        fld = fields[logger.disp_id]
        fldid = logger.disp_id
        fldname = fld.disp_name
        fldunit = fld.unit
        verb = {
            'rising_edge':u'ueberschritten',
            'falling_edge':u'unterschritten',
        }[triggertype]
        
        txt = u'%(fldname)s [ID %(fldid)s]: Der Grenzwert von %(param1)s %(fldunit)s wurde %(verb)s.'%locals()
        
        msg = MIMEText(txt, 'plain', 'utf-8')
        msg['Subject'] = u'Broetje Logger - %(fldname)s'%locals()
        msg['From'] = address
        msg['To'] = address
        t = Thread(target=send_async, args=(msg,))
        t.start()
    return callback