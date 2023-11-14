# This is a Processing.py sketch, see https://py.processing.org for more info and installation instructions.
# The script uses simulation outputs to produce an animation.

import os

# This is used to simplify managing files and directories, and is only used as a part
# of other consts. 
METHOD = 'random'

MAIN_PATH = '~/plane_boarding'
RESULTS_DIR = os.path.join(MAIN_PATH, 'results')

# Note: you may need to modify the suffix to match the simulation parameters.
HISTORY_PATH = os.path.join(RESULTS_DIR, METHOD + '_1.0_16_3_history_0.txt')
BOARDING_ORDER_PATH = os.path.join(RESULTS_DIR, METHOD + '_16_3_boarding_order.txt')


# Used only for displaying
METHOD_LABEL = 'Random'
METHOD_TIME = 528.1

# How many frames per each animation step. The higher the number, the slower the animation.
FRAMES_PER_STEP = 8

# If true, it will save all the frames as images. They can be converted to a movie with a
# Move Maker tool.
SAVE_FRAMES = False

OUTPUT_MOVIE_DIR = os.path.join(MAIN_PATH, 'movie_' + METHOD)
   

TOP_Y = 40                                  # We will start drawing at this Y position

CELL_SIZE = 36                              # Size of the cell
CORRIDOR_WIDTH_HALF = CELL_SIZE / 2         # 1/2 of the corridor width

# Seat is slightly smaller than a cell, so that they won't overlap with each other 
SEAT_MARGIN = 2                             # Seat padding
SEAT_SIZE = CELL_SIZE - SEAT_MARGIN * 2     # Seat size

# Size and spacing between legend boxes.
LEGEND_BOX_SIZE = 18
LEGEND_BOX_MARGIN = 8


# Colors and human-friendly labels for the legend
STATE_TO_COLOR = {
   1: [255, 255, 255],
   2: [255, 133, 133],
   3: [190, 236, 182],
   4: [116, 183, 250],
   5: [239, 144, 42],
   6: [190, 236, 182],
   7: [190, 236, 182],
   8: [190, 236, 182],
   9: [124, 201, 30],
}

# Note: missing states will not be displayed. This is done so that similar states (e.g. seating and reseating,
# moving and vacating a row) will only be listed once. 
STATE_TO_LABEL = {
    2: 'Waiting',
    3: 'Moving',
    4: 'Stowing baggage',
    5: 'Waiting to seat',
    9: 'Seated',
}


# Bunch of global variables to keep the state
n_rows = 0
n_seats_left = 0
n_seats_right = 0
n_dummy_rows = 0
n_passengers = 0

passengers = []
baggage_history = {}
baggage_cnt = 0

boarding_order = []
boarding_order_max = 0        # Max value in the boarding order. Used to scale gradient.

animation_step = 0

is_running = True
frame = 0


class Passenger:
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y
        self.dx = 0.0
        self.dy = 0.0
        self.history = None
        self.current_step = 0


def setup():
    size(1280, 720)
    read_history(HISTORY_PATH)
    read_boarding_order(BOARDING_ORDER_PATH)
    process_animation_step(step=0)


# Reads a single line from the `reader` and splits it by whitespace. 
def parse_line(reader):
    line = reader.readLine()
    if not line:
        return None 
    return map(int, line.split())


# Reads history from a specified file. 
def read_history(path):
    reader = createReader(path)
    global n_rows, n_seats_left, n_seats_right, n_dummy_rows, n_passengers, passengers, baggage_history, baggage_cnt
    n_rows, n_dummy_rows, n_seats_left, n_seats_right, n_passengers, n_baggage = parse_line(reader)
    
    baggage_history = {}
    passengers = [Passenger() for i in range(n_passengers)]
    
    for i in range(n_passengers):
        passengers[i].history = []
        n_entries = parse_line(reader)[0]
        for j in range(n_entries):
            h = dict(zip(['step', 'x', 'y', 'state'], parse_line(reader)))
            passengers[i].history.append(h)
            
    for i in range(n_baggage):
        t, row, side = parse_line(reader)
        if t not in baggage_history:
            baggage_history[t] = []
        baggage_history[t].append({'row': row, 'side': side}) 
        
    baggage_cnt = [[0, 0] for i in range(n_rows + n_dummy_rows)]


# Boarding order is a list of lists.
# i-th element represents i-th row.
def read_boarding_order(path):
    global boarding_order, boarding_order_max
    boarding_order = []
    boarding_order_max = 0
    
    reader = createReader(path)
    while True:
        arr = parse_line(reader)
        if arr is None:
            break
        boarding_order_max = max(boarding_order_max, max(arr))
        boarding_order.append(arr)


def draw_legend(x, y):
    rectMode(CORNER)
    textSize(LEGEND_BOX_SIZE);
    ind = 1 
    for i in range(1, 10):
        # Skip states for which we don't have a label
        if i not in STATE_TO_LABEL:
            continue
        pos_y = y + (LEGEND_BOX_SIZE + LEGEND_BOX_MARGIN) * ind
        col = STATE_TO_COLOR[i]
        fill(col[0], col[1], col[2])
        rect(x, pos_y, LEGEND_BOX_SIZE, LEGEND_BOX_SIZE)
        fill(0)
        text(STATE_TO_LABEL[i], x + LEGEND_BOX_SIZE + 10, pos_y + LEGEND_BOX_SIZE - 3)
        ind += 1


def draw_plane_side(x, y, rows, cols, side):
    bin_height = floor((SEAT_SIZE - (cols - 1) * SEAT_MARGIN) / cols)
    bin_width = floor(SEAT_SIZE / 3)
    bins_x = x - SEAT_MARGIN - bin_width if side == 0 else x + CELL_SIZE * cols + SEAT_MARGIN
    for r in range(rows + n_dummy_rows):
        # We don't draw seats for dummy rows
        if r < n_dummy_rows:
            continue

        for c in range(cols):
            rect(x + c*CELL_SIZE + SEAT_MARGIN, y + r*CELL_SIZE + SEAT_MARGIN, SEAT_SIZE, SEAT_SIZE)



def draw_boarding_order(x, y):
    bin_size = 12
    margin = 4
    posy = y
    colorMode(HSB, 360, 1, 1)
    gradient_start = color(120, 0.7, 0.9) 
    gradient_end = color(0, 0.7, 0.9)
    
    for row in boarding_order:
        for c in range(len(row)):
            if row[c] == -1:
                continue
            
            if boarding_order_max == 0:
                fill(gradient_start)
            else:
                fill(lerpColor(gradient_end, gradient_start, 1.0*row[c]/boarding_order_max))
            rect(x + c * (bin_size + margin), posy, bin_size, bin_size)
        posy += bin_size + margin
    colorMode(RGB, 255, 255, 255)


def draw_passengers(x, y):
    passengers_in_queue = 0
    for p in passengers:
        if p.current_step < 2:
            passengers_in_queue += 1
            continue
        col = STATE_TO_COLOR[p.history[p.current_step-1]['state']] 
        fill(col[0], col[1], col[2])
        circle(x + p.x, y + p.y, 20)
    return passengers_in_queue
        

def update_animation():
    for p in passengers:
        p.x += p.dx
        p.y += p.dy


def calculate_completion_rate():
    cnt = 0
    for p in passengers:
        if p.current_step>0 and p.history[p.current_step-1]['state'] == 9:
            cnt += 1
    return 100.0 * cnt / len(passengers) 
    
    
def process_animation_step(step):
    for p in passengers:
        if p.current_step < len(p.history) and animation_step < p.history[p.current_step]['step']:
            continue

        if p.current_step + 1 >= len(p.history):
            p.dx = 0
            p.dy = 0
            p.current_step = len(p.history)
            continue

        a = p.history[p.current_step]
        b = p.history[p.current_step+1]
        td = b['step'] - a['step'] 
        p.dx = 1.0 * CELL_SIZE * (b['x'] - a['x']) / td / FRAMES_PER_STEP
        p.dy = 1.0 * CELL_SIZE * (b['y'] - a['y']) / td / FRAMES_PER_STEP
        p.x = a['x'] * CELL_SIZE
        p.y = CELL_SIZE / 2 + a['y'] * CELL_SIZE
        p.current_step += 1

    if step in baggage_history:
        for entry in baggage_history[step]:
            baggage_cnt[entry['row']][entry['side']] += 1


def draw():
    global frame, animation_step
    background(255)
    
    # Labels
    fill(0)
    textSize(28)
    text(METHOD_LABEL, 50, 70)
    textSize(22)
    text('Average time: ' + str(METHOD_TIME), 50, 100)
    
    # Boarding order map
    textSize(18)
    text('Boarding zones', 196, 180)
    draw_boarding_order(200, 200)
    
    # Seats
    posx = 0.5 * width
    noFill()
    rectMode(CORNER)
    textSize(14)
    draw_plane_side(posx + CORRIDOR_WIDTH_HALF, TOP_Y, n_rows, n_seats_right, 1)
    draw_plane_side(posx - CORRIDOR_WIDTH_HALF - CELL_SIZE * n_seats_left, TOP_Y, n_rows, n_seats_left, 0)
    
    # Passengers
    passengers_in_queue = draw_passengers(posx, TOP_Y)
    
    # Legend
    stroke(64)
    draw_legend(0.7 * width, 200)
        
    # Stats
    fill(0)
    textSize(18)
    posx = 0.5 * width
    text('Passengers in the queue: ' + str(passengers_in_queue), posx, TOP_Y - 20)
    text('Time: ' + str(animation_step), posx+270, TOP_Y - 20)
    text('Completion: ' + '{0:.1f}'.format(calculate_completion_rate()) + '%', posx+400, TOP_Y - 20)
    
    # Animation
    if is_running:
        # Every `FRAMES_PER_STEP` frames move to the next animation step
        if frame % FRAMES_PER_STEP == 0:
            animation_step += 1
            process_animation_step(animation_step)

        update_animation()
        frame += 1
       
    # Save frame 
    if SAVE_FRAMES:
        saveFrame(os.path.join(OUTPUT_MOVIE_DIR, 'frame-######.png'))


def mouseClicked(): 
    global is_running
    is_running = not is_running
