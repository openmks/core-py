#!/usr/bin/python
import signal
import argparse

co_logger.InitLogger("plotter")

def signal_handler(signal, frame):
	pass
	
def main():
	signal.signal(signal.SIGINT, signal_handler)

	#TODO - Insert argparse to terminal class
	parser = argparse.ArgumentParser(description='')
	parser.add_argument('-v', '--version', action='store_true', help='Version')
	parser.add_argument('create', '', action='store', dest='create', help='')
	parser.add_argument('packager', '', action='store', dest='packager', help='')
    parser.add_argument('-name', '', action='store', dest='name', help='')
    parser.add_argument('-path', '', action='store', dest='path', help='')
	
	args = parser.parse_args()
	
	print("Bye.")

if __name__ == "__main__":
    main()
