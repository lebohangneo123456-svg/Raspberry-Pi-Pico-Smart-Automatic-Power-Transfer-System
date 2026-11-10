
# PROJECT 6: RASPBERRY PI PICO SMART DC TRANSFER SYSTEM
# Proteus 8 / MicroPython / 12 V DC SIMULATION
#
# GP0 = I2C SDA       GP1 = I2C SCL
# GP26 = Main ADC     GP27 = Backup ADC
# GP15 = Main Relay   GP16 = Backup Relay
# GP17 = Buzzer       GP18 = Fault LED
# GP14 = MODE         GP13 = SELECT

from machine import Pin, ADC, I2C
from time import sleep_ms, sleep_us, ticks_ms, ticks_diff

LCD_ADDR = 0x3F
ADC_REFERENCE = 3.3
DIVIDER_RATIO = 5.7

SOURCE_ON_V = 11.2
SOURCE_OFF_V = 10.4

RECOVERY_MS = 1500
FAILURE_MS = 180
DEAD_TIME_MS = 250

SENSOR_PERIOD_MS = 60
SCREEN_PERIOD_MS = 250

# ----------------------------------------
# OUTPUTS: ALL OFF ON STARTUP
# ----------------------------------------

main_relay = Pin(15, Pin.OUT)
backup_relay = Pin(16, Pin.OUT)
buzzer = Pin(17, Pin.OUT)
fault_led = Pin(18, Pin.OUT)

main_relay.value(0)
backup_relay.value(0)
buzzer.value(0)
fault_led.value(0)

# ----------------------------------------
# ANALOG INPUTS
# ----------------------------------------

main_adc = ADC(Pin(26))
backup_adc = ADC(Pin(27))

mode_button = Pin(14, Pin.IN, Pin.PULL_UP)
select_button = Pin(13, Pin.IN, Pin.PULL_UP)


class Button:

    def __init__(self, pin):
        self.pin = pin
        self.raw = pin.value()
        self.stable = self.raw
        self.changed = ticks_ms()

    def pressed(self, now):
        value = self.pin.value()

        if value != self.raw:
            self.raw = value
            self.changed = now

        if value != self.stable:
            if ticks_diff(now, self.changed) >= 45:
                self.stable = value
                return value == 0

        return False


# ----------------------------------------
# I2C LCD DRIVER
# ----------------------------------------

class LCD1602:

    RS = 0x01
    EN = 0x04
    BACKLIGHT = 0x08

    def __init__(self, bus, address):

        self.bus = bus
        self.address = address
        self.rows = [' ' * 16, ' ' * 16]

        sleep_ms(50)

        self._nibble(0x30)
        sleep_ms(5)

        self._nibble(0x30)
        sleep_ms(2)

        self._nibble(0x30)
        sleep_ms(2)

        self._nibble(0x20)

        self.command(0x28)
        self.command(0x08)
        self.command(0x01)

        sleep_ms(3)

        self.command(0x06)
        self.command(0x0C)

    def _raw(self, value):
        self.bus.writeto(
            self.address,
            bytes([value | self.BACKLIGHT])
        )

    def _nibble(self, nibble, rs=False):

        value = (nibble & 0xF0)

        if rs:
            value |= self.RS

        self._raw(value | self.EN)
        sleep_us(200)

        self._raw(value)
        sleep_us(200)

    def _send(self, value, rs=False):

        self._nibble(value & 0xF0, rs)
        self._nibble((value << 4) & 0xF0, rs)

    def command(self, value):

        self._send(value)

        if value == 1 or value == 2:
            sleep_ms(3)

    def line(self, row, message):

        msg = str(message)[:16]
        msg += ' ' * (16 - len(msg))

        old = self.rows[row]

        if msg == old:
            return

        first = 0

        while first < 16 and old[first] == msg[first]:
            first += 1

        last = 15

        while last > first and old[last] == msg[last]:
            last -= 1

        self.command(0x80 | (0x40 * row + first))

        for index in range(first, last + 1):
            self._send(ord(msg[index]), True)

        self.rows[row] = msg


# ----------------------------------------
# VOLTAGE MEASUREMENT
# ----------------------------------------

def measure(adc):

    total = 0

    for i in range(6):
        total += adc.read_u16()

    reading = total / 6.0

    voltage = reading * ADC_REFERENCE
    voltage *= DIVIDER_RATIO
    voltage /= 65535.0

    return voltage


def volts_text(value):

    tenths = int(value * 10.0 + 0.5)

    whole = tenths // 10
    decimal = tenths % 10

    return str(whole) + '.' + str(decimal)


# ----------------------------------------
# SUPPLY VALIDATION WITH HYSTERESIS
# ----------------------------------------

def update_good(
    volts, currently_good, candidate, since, now
):

    threshold = SOURCE_OFF_V

    if not currently_good:
        threshold = SOURCE_ON_V

    wanted = volts >= threshold

    if wanted != candidate:
        candidate = wanted
        since = now

    if wanted != currently_good:

        delay = RECOVERY_MS

        if currently_good:
            delay = FAILURE_MS

        if ticks_diff(now, since) >= delay:
            currently_good = wanted

    return currently_good, candidate, since


def target_source(mode, manual, main_ok, backup_ok):

    if mode == 'AUTO':

        if main_ok:
            return 'MAIN'

        if backup_ok:
            return 'BACKUP'

        return 'OFF'

    if manual == 'MAIN' and main_ok:
        return 'MAIN'

    if manual == 'BACKUP' and backup_ok:
        return 'BACKUP'

    return 'OFF'


# ----------------------------------------
# INITIALIZE LCD
# ----------------------------------------

lcd = None

try:

    bus = I2C(
        0,
        sda=Pin(0),
        scl=Pin(1),
        freq=100000
    )

    addresses = bus.scan()

    print('I2C devices:', addresses)

    if LCD_ADDR in addresses:

        lcd = LCD1602(bus, LCD_ADDR)

        lcd.line(0, 'SMART DC ATS')
        lcd.line(1, 'STARTING...')

    else:
        print('LCD 0x3F not detected')

except Exception as ex:
    print('LCD setup error:', ex)


# ----------------------------------------
# INITIAL SYSTEM STATE
# ----------------------------------------

button_mode = Button(mode_button)
button_select = Button(select_button)

mode = 'AUTO'
manual = 'MAIN'

active = 'OFF'
pending = None

transferring = False
transfer_started = ticks_ms()

main_v = 0.0
backup_v = 0.0

main_good = False
backup_good = False

main_candidate = False
backup_candidate = False

main_since = ticks_ms()
backup_since = main_since

last_sensor = ticks_ms()
last_screen = ticks_ms()
last_report = ticks_ms()

print('PICO SMART 12V ATS READY')


# ----------------------------------------
# MAIN PROGRAM
# ----------------------------------------

while True:

    now = ticks_ms()

    # MODE BUTTON
    if button_mode.pressed(now):

        if mode == 'AUTO':
            mode = 'MANUAL'
        else:
            mode = 'AUTO'

        print('MODE:', mode)

    # SELECT BUTTON
    if button_select.pressed(now):

        if mode == 'MANUAL':

            if manual == 'MAIN':
                manual = 'BACKUP'
            else:
                manual = 'MAIN'

            print('MANUAL REQUEST:', manual)

    # READ BOTH SUPPLY VOLTAGES
    if ticks_diff(now, last_sensor) >= SENSOR_PERIOD_MS:

        last_sensor = now

        main_v = measure(main_adc)
        backup_v = measure(backup_adc)

        main_good, main_candidate, main_since = update_good(
            main_v,
            main_good,
            main_candidate,
            main_since,
            now
        )

        backup_good, backup_candidate, backup_since = update_good(
            backup_v,
            backup_good,
            backup_candidate,
            backup_since,
            now
        )

    desired = target_source(
        mode,
        manual,
        main_good,
        backup_good
    )

    # BREAK-BEFORE-MAKE RELAY TRANSFER
    if transferring:

        pending = desired

        if ticks_diff(now, transfer_started) >= DEAD_TIME_MS:

            main_relay.value(0)
            backup_relay.value(0)

            if pending == 'MAIN':
                main_relay.value(1)

            elif pending == 'BACKUP':
                backup_relay.value(1)

            active = pending
            transferring = False

            print('ACTIVE:', active)

    elif desired != active:

        main_relay.value(0)
        backup_relay.value(0)

        active = 'OFF'
        pending = desired

        transferring = True
        transfer_started = now

        print('TRANSFER TO:', pending)

    # MAIN SUPPLY FAULT LED
    fault_led.value(0 if main_good else 1)

    # BUZZER WARNING
    if active == 'BACKUP' and not main_good:

        if (now % 3000) < 130:
            buzzer.value(1)
        else:
            buzzer.value(0)

    elif not main_good and not backup_good:
        buzzer.value(1)

    else:
        buzzer.value(0)

    # LCD DISPLAY
    if ticks_diff(now, last_screen) >= SCREEN_PERIOD_MS:

        last_screen = now

        if lcd is not None:

            line1 = (
                'M:' + volts_text(main_v)
                + ' B:' + volts_text(backup_v)
            )

            if transferring:
                line2 = 'TRANSFER...'

            elif active == 'OFF':

                prefix = 'AUTO'

                if mode == 'MANUAL':
                    prefix = 'MAN'

                line2 = prefix + ' NO SOURCE'

            else:

                prefix = 'AUTO'

                if mode == 'MANUAL':
                    prefix = 'MAN'

                line2 = prefix + ' ' + active

            try:

                lcd.line(0, line1)
                lcd.line(1, line2)

            except Exception as ex:

                print('LCD error:', ex)
                lcd = None

    # DIAGNOSTIC OUTPUT
    if ticks_diff(now, last_report) >= 2000:

        last_report = now

        print(
            'MAIN:', volts_text(main_v),
            'BACKUP:', volts_text(backup_v),
            'MODE:', mode,
            'ACTIVE:', active
        )

    sleep_ms(10)
