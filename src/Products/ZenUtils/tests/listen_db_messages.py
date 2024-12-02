##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import amqpTestDefns
import sys

state = ""
count = 0

def handlerDecorator(fn):
    def handlerfn(msg):
        sys.stderr.write("%s: Received %s\n" % (fn.__name__, msg.body))
        sys.stderr.flush()
        return fn(msg)
    return handlerfn

# comment out this line to log messages to stderr
handlerDecorator = lambda fn : fn

def printout(s):
    sys.stdout.write(s+"\n")
    sys.stdout.flush()

@handlerDecorator
def messageHandler(msg):
    printout( msg.body )

@handlerDecorator
def statusMessageHandler(msg):
    printout( "%d %s" % (count, state))

@handlerDecorator
def initMessageHandler(msg):
    global count
    count = int(msg.body)

@handlerDecorator
def addrecsMessageHandler(msg):
    global count
    count += int(msg.body)

@handlerDecorator
def stateMessageHandler(msg):
    global state
    state = msg.body

@handlerDecorator
def finMessageHandler(msg):
    sys.exit() 

def main():

    consumer = amqpTestDefns.Consumer()
    consumer.register("ADDRECS", addrecsMessageHandler)
    consumer.register("INIT", initMessageHandler)
    consumer.register("STATE", stateMessageHandler)
    consumer.register("STATUS", statusMessageHandler)
    consumer.register("FIN", finMessageHandler)

    printout("ready")

    try:
        consumer.wait()
    except Exception as e:
        printout("exiting with error...")
        printout(e)
        raise
    finally:
        consumer.close()
        print "exiting..."

if __name__ == "__main__":
    main()
