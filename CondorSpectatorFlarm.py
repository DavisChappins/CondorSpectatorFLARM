import json
import math
import socket
import time
import threading
from math import atan2, cos, sin, sqrt, radians, tan

# https://delta-omega.com/download/EDIA/FLARM_DataportManual_v3.02E.pdf
# https://www.condorsoaring.com/wp-content/uploads/2021/09/condor-2-manual-1.pdf

def dmm_mmm_direction_to_dd_ddddd(coord_str):
    # Extract the direction (N, S, E, or W) from the end of the input string
    direction = coord_str[-1]
    # Remove the direction part to get the coordinate without it
    coord_str = coord_str[:-1]
    
    # Split the input string into degrees, minutes, and milliseconds
    degrees_str, minutes_str, milliseconds_str = coord_str.split('.')
    
    # Convert degrees, minutes, and milliseconds to integers
    degrees = int(degrees_str)
    minutes = int(minutes_str)
    milliseconds = int(milliseconds_str)
    
    # Calculate the decimal degrees with additional decimal places
    decimal_degrees = degrees + (minutes + milliseconds / 1000) / 60.0
    
    # Add the appropriate sign for latitude (N or S) and longitude (E or W)
    if direction in ['S', 'W']:
        decimal_degrees = -decimal_degrees
    
    result_str = format(decimal_degrees, ".6f")
    
    return float(result_str)

def ensure_six_characters(input_str):
    # Check if the input string is already 6 characters or longer
    if len(input_str) >= 6:
        return input_str[:6]  # Take the first 6 characters and discard the rest
    else:
        # Fill in the remaining characters with "F"
        return input_str.ljust(6, 'F')

def convert_to_hex(input_str):
    try:
        # Convert the input string to a hexadecimal representation
        hex_value = input_str.encode('utf-8').hex().upper()
        
        # Ensure the hexadecimal representation is 6 characters long
        if len(hex_value) < 6:
            hex_value = hex_value.ljust(6, 'F')
        
        return hex_value[:6]  # Truncate to 6 characters if longer
    except Exception as e:
        return f"Error: {str(e)}"

def haversine_distance(lat1, lon1, lat2, lon2):
    # Radius of the Earth in meters
    R = 6371000  # Mean radius of the Earth

    # Convert latitude and longitude from degrees to radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    # Differences in latitude and longitude
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Calculate the distance in meters
    distance = R * c

    return distance

def calculate_relative_distances(lat1, lon1, lat2, lon2):
    distance = haversine_distance(lat1, lon1, lat2, lon2)

    # Calculate the initial bearing (not used in this code, but included for completeness)
    dlon = radians(lon2) - radians(lon1)
    y = sin(dlon) * cos(radians(lat2))
    x = cos(radians(lat1)) * sin(radians(lat2)) - sin(radians(lat1)) * cos(radians(lat2)) * cos(dlon)
    initial_bearing = atan2(y, x)

    # Calculate the relative distances
    relative_east = round(distance * sin(initial_bearing))
    relative_north = round(distance * cos(initial_bearing))

    return relative_east, relative_north

def calculate_relative_vertical_distance(altitude1, altitude2):
    return altitude2 - altitude1

def feet_to_meters(feet):
    meters = float(feet) * 0.3048
    return meters

def string_to_number(input_string):
    try:
        number = int(input_string)
        return number
    except ValueError:
        print("Invalid input: not a valid integer")
        return None

def knots_to_mps(knots):
    # 1 knot is equal to 0.514444 meters per second
    meters_per_second = float(knots) * 0.514444
    
    # Round the distances to one decimal place
    meters_per_second = round(meters_per_second, 1)
    
    return meters_per_second

def calculate_nmea_checksum(sentence):
    # Remove the leading '$' and trailing '*' if present
    sentence = sentence.strip('$')
    sentence = sentence.rstrip('*')

    # Initialize the checksum with 0
    checksum = 0

    # XOR each character in the sentence
    for char in sentence:
        checksum ^= ord(char)

    # Convert the checksum to a hexadecimal string
    checksum_hex = hex(checksum)[2:].upper()

    # Ensure the checksum is two characters long
    if len(checksum_hex) == 1:
        checksum_hex = '0' + checksum_hex

    return checksum_hex

def calculate_nmea_sentence(sentence):
    # Calculate checksum
    chk = calculate_nmea_checksum(sentence)
    
    # Add checksum to sentence with newline
    message = sentence + '*' + chk + '\n'
    
    return message

def calculate_alert_radius(t_RelativeEast, t_RelativeNorth):
    alert_radius = math.sqrt(t_RelativeEast**2 + t_RelativeNorth**2)
    return alert_radius

def calculate_t_AlarmLevel(t_RelativeVertical, t_RelativeEast, t_RelativeNorth):
    alert_radius = calculate_alert_radius(t_RelativeEast, t_RelativeNorth)

    if abs(t_RelativeVertical) < 50 and alert_radius < 100:
        return 2
    elif abs(t_RelativeVertical) < 100 and alert_radius < 400:
        return 1
    else:
        return 0

def parse_json_from_file(file_path):
    retry_delay = 15
    try:
        with open(file_path, 'r') as file:
            json_string = file.read().strip()
        
        # Parse the JSON data
        parsed_data = json.loads(json_string)
        
        # Verify that the data is a list
        if isinstance(parsed_data, list):
            return parsed_data
        else:
            print("JSON data is not a list as expected.")
            return None

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        time.sleep(retry_delay)
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        time.sleep(retry_delay)
        return None
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        time.sleep(retry_delay)
        return None

# Function to run parse_json_from_file in a separate thread (if needed in future)
def run_parse_json():
    global parsed_data  # Access the global variable parsed_data
    while True:
        parsed_object = parse_json_from_file(file_path)

# Create a lock for thread-safe access to parsed_data
# lock = threading.Lock()
# parsed_data = None

# Path to the JSON file
file_path = r"C:\Condor3\Logs\spectate.json"

# Define the target IP address and port
target_ip = '127.0.0.1'  # Replace with the IP address you want to send to
target_port = 4352  # Replace with the port number you want to use

# URL of the JSON endpoint is no longer needed
# url = "http://127.0.0.1:8080/allPilots"

# Removed threading as the main loop handles reading the file

Target_CN = "DC1"
Target_CN_hex = convert_to_hex(Target_CN)
print('Target CN:', Target_CN, 'in hex:', Target_CN_hex)

# Loop target time for all UDP traffic as to not overwhelm XCSOAR
target_time = 1.0  # seconds

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print('Grabbing data from:', file_path)
print('Sending data to:', target_ip, 'port:', target_port)

while True:
    # Dynamic loop time
    start_time = time.time()
    
    # Call the parse_json_from_file function
    parsed_object = parse_json_from_file(file_path)
    
    if parsed_object is None:
        # If parsing failed, skip this iteration and retry
        print('Failed to parse JSON data. Retrying...')
        time.sleep(1)
        continue

    try:
        index = next((i for i, entry in enumerate(parsed_object) if entry.get('CN') == Target_CN), None)
        if index is None:
            print(f"Cannot find ownship with CN='{Target_CN}'. Waiting 10 seconds...")
            time.sleep(10)
            continue

        # Define ownship
        ownship = parsed_object[index]
        ownship_lat = dmm_mmm_direction_to_dd_ddddd(ownship['latitude'])
        ownship_lon = dmm_mmm_direction_to_dd_ddddd(ownship['longitude'])
        # ownship_alt = feet_to_meters(ownship['altitude'])
        ownship_alt = float(ownship['altitude'])

        # Calculate number of ships
        numships = len(parsed_object)
        # print(numships)
        
        # Iterate through list, skip ownship (if no skip then ownship object present (OK))
        for i in range(numships):
            # Convert condor format to PFLAA format
            testship = parsed_object[i]  # testing

            # Relative north, relative east
            a_lat = dmm_mmm_direction_to_dd_ddddd(testship['latitude'])
            a_lon = dmm_mmm_direction_to_dd_ddddd(testship['longitude'])

            t_RelativeEast, t_RelativeNorth = calculate_relative_distances(ownship_lat, ownship_lon, a_lat, a_lon)  # meters

            # Relative vertical
            # a_alt = feet_to_meters(testship['altitude'])
            a_alt = float(testship['altitude'])
            # print('alt:',a_alt)
            
            t_RelativeVertical = round(a_alt - ownship_alt)  # meters
           
            # Alarm level
            t_AlarmLevel = calculate_t_AlarmLevel(t_RelativeVertical, t_RelativeEast, t_RelativeNorth)

            # ID type = 1
            t_IDType = 1

            # ID (hexadecimal of CN)
            t_ID = convert_to_hex(testship['CN'])

            # Track
            t_Track = string_to_number(testship['heading'])
            if t_Track is None:
                t_Track = 0  # Default value if conversion fails

            # Turn rate = 0
            t_TurnRate = ''

            # Groundspeed
            # t_GroundSpeed = knots_to_mps(testship['speed'])  # m/s
            t_GroundSpeed = testship['speed']

            # Climb rate
            # t_ClimbRate = knots_to_mps(testship['vario'])  # m/s
            t_ClimbRate = testship['vario']
            # print('id:',t_ID,'climb (kts):',testship['vario'],'(mps)',t_ClimbRate,'rel vert',t_RelativeVertical)

            # Type = 1
            t_Type = 1
            
            # print(t_AlarmLevel,t_RelativeVertical,t_RelativeEast,t_RelativeNorth)
            
            # Send ship via UDP
            try:
                # Message to send
                # message = "$PFLAA,0,-1234,1234,220,2,DD8F12,180,-4.5,30,-1.4,1*\n"
                if t_RelativeNorth != 0 and t_RelativeEast != 0:
                    
                    message = "$PFLAA," + str(t_AlarmLevel) + "," + str(t_RelativeNorth) + "," + str(t_RelativeEast) + "," + str(t_RelativeVertical) + "," + str(t_IDType) + "," + str(t_ID) + "," + str(t_Track) + "," + str(t_TurnRate) + "," + str(t_GroundSpeed) + "," + str(t_ClimbRate) + "," + str(t_Type)
                    # message = "$PFLAA,"+str(t_AlarmLevel)+","+str(-1000)+","+str(1000)+","+str(15)+","+str(t_IDType)+","+str("ABC123")+","+str(t_Track)+","+str(5)+","+str(200)+","+str(15)+","+str(1)

                    msg = calculate_nmea_sentence(message)
                    # print(msg)
                    # Send the message to the target IP and port
                    sock.sendto(msg.encode('utf-8'), (target_ip, target_port))
                else:
                    # print('not sending',t_ID)
                    pass
                # print(f"Sent '{message}' to {target_ip}:{target_port}")
                # if i==0:
                    # print(t_RelativeNorth, t_RelativeEast)

            finally:
                time.sleep(0.00001)

        # Dynamic loop timing        
        end_time = time.time()
        elapsed_time = end_time - start_time
        print("elapsed_time", elapsed_time)
        time_difference = target_time - elapsed_time
        print("time_difference", time_difference)
        # print(time_difference)
        if time_difference > 0:
            # Sleep for the remaining time to reach the target
            time.sleep(time_difference)
    except Exception as e:
        print(e)
        print('Cannot find', Target_CN, 'waiting 10 seconds...')
        time.sleep(10)
        pass

