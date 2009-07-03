# encoding=utf-8
import os.path
import threading
import random
import textwrap
import struct
import traceback
import datetime
import StringIO
try:
    import cPickle as pickle
except ImportError:
    import pickle
from chunk import Chunk
from array import array

class StoryError(Exception): pass
class QuetzalError(Exception): pass

OPCODE_FORMAT_SHORT = 1
OPCODE_FORMAT_LONG = 2
OPCODE_FORMAT_VARIABLE = 3
OPCODE_FORMAT_EXTENDED = 4

OPERAND_TYPE_SMALL = 1
OPERAND_TYPE_LARGE = 0
OPERAND_TYPE_VAR = 2
OPERAND_TYPE_OMITTED = 3

STORY_MAX_SIZE = 131072

COMPRESS_SAVE_FILES = True

EXTRA_CHARACTERS = (
    'ä', 'ö', 'ü',
    'Ä', 'Ö', 'Ü',
    'ß', '«', '»',
    'ë', 'ï', 'ÿ',
    'Ë', 'Ï', 'á',
    'é', 'í', 'ó', 
    'ú', 'ý', 'Á',
    'É', 'Í', 'Ó',
    'Ú', 'Ý', 'à',
    'è', 'ì', 'ò',
    'ù', 'À', 'È',
    'Ì', 'Ò', 'Ù',
    'â', 'ê', 'î',
    'ô', 'û', 'Â',
    'Ê', 'Î', 'Ô',
    'Û', 'å', 'Å',
    'ø', 'Ø', 'ã',
    'ñ', 'õ', 'Ã',
    'Ñ', 'Õ', 'æ',
    'Æ', 'ç', 'Ç',
    'þ', 'ð', 'Þ',
    'Ð', '£', 'œ',
    'Œ', '¡', '¿',
)

TEXT_STYLE_ROMAN = 0
TEXT_STYLE_REVERSE_VIDEO = 1
TEXT_STYLE_BOLD = 2
TEXT_STYLE_ITALIC = 4
TEXT_STYLE_FIXED_PITCH = 8

COLOUR_MAPPINGS = {
    2: '01',
    3: '04',
    4: '09',
    5: '08',
    6: '12',
    7: '13',
    8: '11',
    9: '00',
    10: '14',
}

class ZMachine(threading.Thread):
    # IRC/output management
    irc = None
    channel = None
    output_buffer = ''
    text_style = 
    
    # Thread management
    awaiting_input = False
    input_wait = None
    input_text = None
    
    # Story management
    story = None
    version = 0
    
    # Memory management
    memory = None
    memory_dynamic_end = 0
    memory_static_start = 0
    memory_static_end = 0
    memory_high_start = 0
    memory_high_end = 0
    
    # Table locations
    dictionary_start = 0
    object_table_start = 0
    global_variable_start = 0
    abbreviation_start = 0
    
    # Lexical parsing stuff
    word_separators = []
    dictionary_entry_length = 0
    dictionary_length = 0
    
    # Exceution stuff
    pc = 0
    stack = None
    call_stack = None
    running = False
    
    # Stats
    opcodes_executed = 0
    inputs_requested = 0
    lines_output = 0
    
    # Output streams
    stream_1 = True # Screen
    stream_2 = False # Transcript
    stream_3 = [] # Tables in memory (can be nested)
    stream_4 = False # Player script file
    
    # Colours (changing these will change the defaults)
    colour_fg = 2
    colour_bg = 9
    
    # Z-Char parsing
    a0 = 'abcdefghijklmnopqrstuvwxyz'
    a1 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    a2 = ' 0123456789.,!?_#\'"/\\<-:()'
    
    def __init__(self, irc, channel, story):
        self.irc = irc
        self.channel = channel
        self.story = "data/zmachine/stories/%s" % story.replace('/','')
        if not os.path.isfile(self.story):
          raise IOError, "%s does not exist!" % story
        threading.Thread.__init__(self, name="%s/%s/%s" % (irc.network.name, channel, story))
        
    def run(self):
        self.load_story()
        self.complete_vm_setup()
        if not self.running:
            self.running = True
            self.main_loop()
    
    def load_story(self):
        f = open(self.story, 'rb')
        self.memory = array('B') # Unsigned
        try:
            self.memory.fromfile(f, STORY_MAX_SIZE)
        except EOFError:
            pass
        f.close()
    
    def complete_vm_setup(self):        
        self.version = self.memory[0x00]
        if self.version > 5:
            raise StoryError, "Unsupported version"
        
        self.memory_high_end = len(self.memory) - 1
        self.memory_dynamic_end = self.unsigned_number(0x0E)
        self.memory_static_start = self.memory_dynamic_end + 1
        self.memory_static_end = len(self.memory) - 1
        if self.memory_static_end < 0xFFFF:
            self.memory_static_end = 0xFFFF
        self.memory_high_start = self.unsigned_number(0x04)
        
        self.dictionary_start = self.unsigned_number(0x08)
        self.object_table_start = self.unsigned_number(0x0A)
        self.global_variable_start = self.unsigned_number(0x0C)
        self.abbreviation_start = self.unsigned_number(0x18)
        
        self.pc = self.unsigned_number(0x06)
        
        self.stack = array('H')
        self.call_stack = array('I')
        
        self.opcodes_executed = 0
        self.inputs_requested = 0
        self.lines_output = 0
        
        # Set up the dictionary
        n = self.memory[self.dictionary_start] + self.dictionary_start + 1
        self.word_separators = self.memory[self.dictionary_start + 1:n]
        self.dictionary_entry_length = self.memory[n]
        self.dictionary_length = self.unsigned_number(n + 1)
        
        # Create a lock
        self.input_wait = threading.Event()
        
        # Prepare Z-Char dicts
        if self.version != 1:
            self.a2 = " \n0123456789.,!?_#'\"/\\-:()"
        
        # Set up colours
        self.memory[0x01] |= 0x01
        self.memory[0x2C] = self.colour_bg
        self.memory[0x2D] = self.colour_fg
        
        # Note what we can't do (sound, pictures, undo, mouse, menus)
        self.memory[0x10] &= ~0xDC # ~11011100
        
        # Set up screen size. We call it 100 wide for no particular reason.
        self.memory[0x20] = 255 # Infinite height.
        self.memory[0x21] = 100
        if self.version >= 5:
            self.set_number(0x22, self.memory[0x20])
            self.set_number(0x24, self.memory[0x21])
        
        logger.info("Loaded version %s story file from %s" % (self.version, self.story))
        logger.info("dynamic_end: %s, static_end: %s, high_start: %s" % (self.memory_dynamic_end, self.memory_static_end, self.memory_high_start))
        logger.info("dictionary_start: %s, dictionary_entry_length: %s, object_table_start: %s global_variable_start: %s, abbrevation_start: %s" % (
            self.dictionary_start,
            self.dictionary_entry_length,
            self.object_table_start,
            self.global_variable_start,
            self.abbreviation_start
        ))
        logger.info("pc: %s" % self.pc)
        
    def main_loop(self):
        logger.debug("%s: Running main loop" % self.getName())
        while self.running:
            self.execute_cycle()
            
    def report_error(self, error):
        self.running = False
        lines = error.strip().split("\n")
        for line in lines:
            m('irc_helpers').message(self.irc, self.channel, "~B[Z] Fatal error~B: %s" % line)
        logger.error("Fatal error in %s: %s" % (self.getName(), error))

    # Useful utility functions
    def unsigned_number(self, address):
        if address > self.memory_high_end - 1:
            raise StoryError, "Attempt to retrieve data from past the end of high memory"
        top = self.memory[address] << 8
        bottom = self.memory[address + 1]
        return top | bottom
    
    def signed_number(self, address):
        return self.sign(self.unsigned_number(address))
        
    def sign(self, unsigned, bits=16):
        if unsigned & (1 << (bits - 1)):
            return unsigned - (1 << bits)
        return unsigned
        
    def set_number(self, address, number):
        high = (number >> 8) & 0xFF
        low = number & 0xFF
        self.memory[address] = high
        self.memory[address + 1] = low
        
    def unpack_address(self, address):
        if self.version <= 3:
            return 2 * address
        elif self.version <= 7:
            return 4 * address
        elif self.version == 8:
            return 8 * address
    
    def z_string(self, address, word_address=False):
        string = []
        if word_address:
            address *= 2
        while True:
            word = self.unsigned_number(address)
            string.append((word & 0x7C00) >> 10)
            string.append((word & 0x03E0) >> 5)
            string.append((word & 0x001F))
            if word & 0x8000:
                break
            address += 2
        return string
    
    def zchar_to_zscii(self, zstring, allow_abbreviation_expansion=True):
        zscii = []
        alphabet = 0
        last_alphabet = 0
        temporary = False
        i = 0
        while i < len(zstring):
            if i >= len(zstring):
                break
            zchar = zstring[i]
            if (self.version < 3 and zchar == 2) or zchar == 4:
                last_alphabet = alphabet
                alphabet = (alphabet + 1) % 3
                temporary = (zchar == 2 or self.version >= 3) 
            elif (self.version < 3 and zchar == 3) or zchar == 5:
                last_alphabet = alphabet
                alphabet = (alphabet + 2) % 3
                temporary = (zchar == 3 or self.version >= 3)
            else:
                if zchar == 0:
                    # 0 is a space.
                    zscii.append(32)
                elif zchar == 1 and self.version == 1:
                    zscii.append(13)
                elif zchar <= 3 and self.version >= 2 and allow_abbreviation_expansion:
                    if zchar == 1 or self.version >= 3:
                        i += 1
                        offset = zstring[i]
                        zchar_abbr = self.z_string(self.unsigned_number(self.abbreviation_start + 2 * ((32 * (zchar - 1)) + offset)), True)
                        abbr = self.zchar_to_zscii(zchar_abbr, False)
                        zscii.extend(abbr)
                elif zchar == 6 and alphabet == 2:
                    # 10-bit escape code! Whoever designed this was insane.
                    if i + 2 >= len(zstring):
                        break
                    high = zstring[i + 1] << 5
                    low = zstring[i + 2]
                    i += 2
                    result = high | low
                    zscii.append(result)
                elif zchar >= 6:
                    index = zchar - 6
                    if alphabet == 0:
                        result = ord(self.a0[index])
                    elif alphabet == 1:
                        result = ord(self.a1[index])
                    elif alphabet == 2:
                        result = ord(self.a2[index])
                    zscii.append(result)
                else:
                    logger.warn("Unknown Z-character %s!" % zchar)
                if temporary:
                    alphabet = last_alphabet
            i += 1
        return zscii

    def zscii_to_ascii(self, zscii):
        ascii = ''
        for char in zscii:
            if char >= 32 and char <= 126:
                ascii += chr(char)
            elif char >= 155 and char <= 251:
                ascii += EXTRA_CHARACTERS[char - 155]
            elif char == 13 or char == 10:
                ascii += "\n"
        return ascii
    
    def ascii_to_zscii(self, ascii):
        zscii = []
        for char in ascii:
            o = ord(char)
            if o >= 32 and o <= 126:
                zscii.append(o)
            elif char == "\n":
                zscii.append(10)
            elif char == "\r":
                pass
            elif char in EXTRA_CHARACTERS:
                zscii += list(EXTRA_CHARACTERS).index(char)
            else:
                zscii.append(ord("?"))
        return zscii
    
    def zscii_to_zchar(self, zscii, bytes):
        zchars = []
        zchar_limit = bytes / 2 * 3
        for i in range(0, len(zscii)):
            char = chr(zscii[i])
            pos = self.a0.find(char)
            if char == ' ':
                zchars.append(0)
            elif pos > -1:
                zchars.append(pos + 6)
            else:
                pos = self.a1.find(char)
                if pos > -1:
                    zchars.append(4)
                    zchars.append(pos + 6)
                else:
                    pos = self.a2.find(char)
                    if pos > -1:
                        zchars.append(5)
                        zchars.append(pos + 6)
                    else:
                        zchars.append(0)
                        
        while len(zchars) < zchar_limit:
            zchars.append(5)
        
        zchars = zchars[0:zchar_limit]
        words = []
        for i in range(0, zchar_limit, 3):
            word = 0
            if i >= zchar_limit - 3:
                word |= 0x8000 # Set end-of-string flag
            word |= zchars[i] << 10
            word |= zchars[i+1] << 5
            word |= zchars[i+2]
            high_byte = word >> 8
            low_byte = word & 0xFF
            words.append(high_byte)
            words.append(low_byte)
        
        if len(words) > bytes:
            raise StoryError, "More bytes than permitted in zscii_to_zchar!"
        
        return words
        
    def locate_string_in_dictionary(self, zstring):
        start = self.dictionary_start + self.memory[self.dictionary_start] + 4
        k = self.dictionary_entry_length
        for i in range(0, self.dictionary_length):
            if list(self.memory[start + i*k:start + i*k + 4]) == zstring:
                return start + i*k
            elif self.memory[start + i*k] > zstring[0]:
                return 0
        return 0
    
    def tokenise_zscii(self, table_address, zscii):
        words = []
        next_word = []
        last_new_word = 0
        for i in range(0, len(zscii)):
            char = zscii[i]
            if char == 32:
                if len(next_word) > 0:
                    words.append((last_new_word, next_word))
                    next_word = []
                last_new_word = i + 1
            elif char in self.word_separators:
                if len(next_word) > 0:
                    words.append((last_new_word, next_word))
                    next_word = []
                words.append((i, [char]))
                last_new_word = i + 1
            else:
                next_word.append(char)
        
        if len(next_word) > 0:
            words.append((last_new_word, next_word))
        self.memory[table_address + 1] = len(words)
        for i in range(0, len(words)):
            if i >= self.memory[table_address]:
                break
            word_data = words[i]
            word = word_data[1]
            zstring = self.zscii_to_zchar(word, 4)
            pos = self.locate_string_in_dictionary(zstring)
            self.set_number(table_address + i*4 + 2, pos)
            self.memory[table_address + i*4 + 4] = len(word)
            self.memory[table_address + i*4 + 5] = word_data[0] + 1
    
    def execute_cycle(self):
        opcode = self.memory[self.pc]
        format = 0
        operand_count = -1
        operand_types = []
        really_variable = False
        
        
        if self.version >= 5 and opcode == 0xBE:
            format = OPCODE_FORMAT_EXTENDED
            really_variable = True
            self.pc += 1
            opcode = self.memory[self.pc]
        elif (opcode & 0xC0) == 0xC0:
            format = OPCODE_FORMAT_VARIABLE
            if (opcode & 0x20) == 0:
                operand_count = 2
            else:
                really_variable = True
            opcode &= 0x1F
        elif (opcode & 0x80) == 0x80:
            format = OPCODE_FORMAT_SHORT
            if (opcode & 0x30) == 0x30:
                operand_count = 0
            else:
                operand_count = 1
                if (opcode & 0x30) == 0x00:
                    operand_types = [OPERAND_TYPE_LARGE]
                elif (opcode & 0x10) == 0x10:
                    operand_types = [OPERAND_TYPE_SMALL]
                elif (opcode & 0x20) == 0x20:
                    operand_types = [OPERAND_TYPE_VAR]
                else:
                    raise StoryError, "Nonsense in execute_cycle! PC = %s, opcode = %s, OPERAND_FORMAT_SHORT" % (self.pc, opcode)
            opcode &= 0x0F
        else:
            format = OPCODE_FORMAT_LONG
            operand_count = 2
            operand_types = [OPERAND_TYPE_SMALL, OPERAND_TYPE_SMALL]
            if (opcode & 0x40) == 0x40:
                operand_types[0] = OPERAND_TYPE_VAR
            if (opcode & 0x20) == 0x20:
                operand_types[1] = OPERAND_TYPE_VAR
            opcode &= 0x1F
        
        if format == OPCODE_FORMAT_VARIABLE or format == OPCODE_FORMAT_EXTENDED:
            def figure_types(bits):
                for i in range(0, 4):
                    now = (bits >> (3 - i) * 2) & 0x03
                    if now == OPERAND_TYPE_SMALL:
                        operand_types.append(OPERAND_TYPE_SMALL)
                    elif now == OPERAND_TYPE_LARGE:
                        operand_types.append(OPERAND_TYPE_LARGE)
                    elif now == OPERAND_TYPE_VAR:
                        operand_types.append(OPERAND_TYPE_VAR)
                    else:
                        break
            self.pc += 1
            figure_types(self.memory[self.pc])
            
            # Because call_vn2 and call_vs2 are annoying special cases.
            if format == OPCODE_FORMAT_VARIABLE:
                if opcode == 0xC or opcode == 0x1A:
                    self.pc += 1
                    figure_types(self.memory[self.pc])
            
            operand_count = len(operand_types)
        
        operands = []
        for operand_type in operand_types:
            if operand_type == OPERAND_TYPE_LARGE:
                operands.append(self.unsigned_number(self.pc + 1))
                self.pc += 2
            elif operand_type == OPERAND_TYPE_SMALL or operand_type == OPERAND_TYPE_VAR:
                self.pc += 1
                operands.append(self.memory[self.pc])
        
        function_name = 'op_'
        if format == OPCODE_FORMAT_VARIABLE and really_variable:
            function_name += 'var'
        elif foramt == OPCODE_FORMAT_EXTENDED:
            function_name += 'ext'
        else:
            function_name += "%sop" % operand_count
        function_name += "_%s" % hex(opcode)[2:]
        
        if hasattr(self, function_name):
            # Resolve variables
            for i in range(0, operand_count):
                if operand_types[i] == OPERAND_TYPE_VAR:
                    operands[i] = self.get_variable(operands[i])
            
            try:
                self.__getattribute__(function_name)(*operands)
            except StoryError, message:
                self.report_error("Story error: %s" % message)
            except Exception, message:
                self.report_error("Internal error: %s" % message)
                self.report_error(traceback.format_exc())
            else:
                self.opcodes_executed += 1
        else:
            self.report_error("unknown opcode %s (%s)" % (function_name, opcode))
        
        self.pc += 1
    
    def get_variable(self, variable, signed=False):
        value = 0
        if variable == 0x00:
            value = self.stack.pop()
        elif variable >= 0x10:
            if variable > 0xFF:
                raise StoryError, "Attempted to read illegal global variable %s" % variable
            address = self.global_variable_start + ((variable - 0x10) * 2)
            if signed:
                value = self.signed_number(address)
            else:
                value = self.unsigned_number(address)
        elif len(self.call_stack) > 0:
            value = self.stack[self.call_stack[-1] + variable - 1]
        else:
            value = self.stack[variable - 1]
        value &= 0xFFFF
        return value
        
    def set_variable(self, variable, value):
        value &= 0xFFFF
        if variable == 0x00:
            self.stack.append(value)
        elif variable >= 0x10:
            if variable > 0xFF:
                raise StoryError, "Attempted to write illegal global variable %s" % variable
            address = self.global_variable_start + ((variable - 0x10) * 2)
            self.set_number(address, value)
        elif len(self.call_stack) > 0:
            self.stack[self.call_stack[-1] + variable - 1] = value
        else:
            self.stack[variable - 1] = value
    
    def get_object_address(self, obj):
        if obj < 0 or (obj > 255 and self.version < 4) or (obj > 65536 and self.version >= 5):
            raise StoryError, "Attempted to find invalid object %s" % obj
        if obj == 0:
            return 0
        address = self.object_table_start + (61 if self.version < 4 else 126) + (obj - 1) * (9 if self.version < 4 else 14)
        return address
    
    def get_object_attribute(self, obj, attribute):
        if (attribute > 31 and self.version < 4) or (attribute > 47 and self.version >= 4):
            raise StoryError, "Attempted to get invalid attribute %s" % obj
        if obj == 0:
            raise StoryError, "Attempted to read attribute from null object"
        address = self.get_object_address(obj)
        bits = 0x80 >> (attribute % 8)
        part = attribute // 8
        return bool(self.memory[address + part] & bits)
        
    def set_object_attribute(self, obj, attribute, value):
        if (attribute > 31 and self.version < 4) or (attribute > 47 and self.version >= 4):
            raise StoryError, "Attempted to set invalid attribute %s" % obj
        if obj == 0:
            raise StoryError, "Attempted to set attribute on null object"
        address = self.get_object_address(obj)
        bits = 0x80 >> (attribute % 8)
        part = attribute // 8
        if not value:
            self.memory[address + part] &= ~bits
        else:
            self.memory[address + part] |= bits
    
    def get_object_property_table_address(self, obj):
        if obj == 0:
            raise StoryError, "Attempted to read property table for null object"
        address = self.get_object_address(obj)
        return self.unsigned_number(address + (7 if self.version < 4 else 12))
    
    def get_object_name(self, obj):
        if obj == 0:
            raise StoryError, "Attempted to get name of null object"
        address = self.get_object_property_table_address(obj)
        return self.z_string(address + 1)
    
    def get_object_property_address(self, obj, prop):
        address = self.get_object_property_table_address(obj)
        address += self.memory[address]*2 + 1
        if self.version < 4:
            while self.memory[address] != 0:
                property_number = self.memory[address] % 32
                size = self.memory[address] // 32 + 1
                if property_number == prop:
                    return address + 1
                elif property_number < prop:
                    return 0
                address += size + 1
        else:
            # I have no idea if this is the right loop condition.
            # The Standard doesn't specify.
            while self.memory[address] != 0:
                property_number = self.memory[address] & 0x3F
                bytes = 2 if (self.memory[address] & 0x80) else 1
                if property_number == prop:
                    return address + bytes
                if bytes == 1:
                    size = 1
                else:
                    size = self.memory[address + 1] & 0x3F
                    if size == 0:
                        size = 64
                address += size + bytes
        return 0
    
    def get_default_property_address(self, prop):
        return self.object_table_start + (prop - 1) * 2
    
    def get_property_size(self, obj=0, prop=0, address=0):
        if not address:
            address = self.get_object_property_address(obj, prop)
        address -= 1
        if self.version < 4:
            return self.memory[address] // 32 + 1
        else:
            if self.memory[address] & 0x80:
                size = self.memory[address] & 0x3F
                if size == 0:
                    size = 64
                return size
            else:
                return 1
    
    def get_object_parent(self, obj=0, address=0):
        if obj == 0 and address == 0:
            return 0
        if address == 0:
            address = self.get_object_address(obj)
        if self.version < 4:
            return self.memory[address + 4]
        else:
            return self.unsigned_number(address + 6)
    
    def get_object_sibling(self, obj=0, address=0):
        if obj == 0 and address == 0:
            raise StoryError, "Attempted to find the sibling of null object"
        if address == 0:
            address = self.get_object_address(obj)
        if self.version < 4:
            return self.memory[address + 5]
        else:
            return self.unsigned_number(address + 8)
    
    def get_object_child(self, obj=0, address=0):
        if obj == 0 and address == 0:
            raise StoryError, "Attempted to find the child of the null object"
        if address == 0:
            address = self.get_object_address(obj)
        if self.version < 4:
            return self.memory[address + 6]
        else:
            return self.unsigned_number(address + 10)
    
    def set_object_parent(self, obj=0, new_parent=0, address=0):
        if 
        address = self.get_object_address(obj)
        if self.version < 4:
            self.memory[obj_address + 4] = new_parent
    
    def get_object_previous_sibling(self, obj):
        object_parent = self.get_object_parent(obj)
        if object_parent > 0:
            parent_child = self.get_object_child(object_parent)
            if parent_child == obj:
                return 0
            else:
                this_object = parent_child
                while True:
                    address = self.get_object_address(this_object)
                    next_sibling = self.get_object_sibling(this_object)
                    if next_sibling == obj:
                        return this_object
                    else:
                        this_object = next_sibling
                        if this_object == 0:
                            raise StoryError, "The tree is not well-founded. D:"
        return 0
    
    def print_string(self, ascii):
        if len(self.stream_3) > 0:
            zchars = self.ascii_to_zscii(ascii)
            self.memory[self.stream_3[-1]:self.stream_3[-1]+len(zchars)] = zchars
            self.stream_3[-1] += len(zchars)
        elif self.stream_1:
            if self.version >= 5:
                formats = ''
                if self.text_style & TEXT_STYLE_REVERSE_VIDEO:
                    formats += chr(22)
                if self.text_style & TEXT_STYLE_BOLD:
                    formats += chr(2)
                if self.text_style & TEXT_STYLE_ITALIC:
                    formats += chr(31)
                if self.colour_fg != 2 or self.colour_bg != 9:
                    ascii = "\x02\x03%s,%s%s\x03\x02" % (COLOUR_MAPPINGS[self.colour_fg], COLOUR_MAPPINGS[self.colour_bg], ascii)
                ascii = '%s%s%s' % (formats, ascii, formats[::-1])
            self.display_string(ascii)
    
    def display_string(self, ascii):
        self.output_buffer += ascii
        lines = self.output_buffer.split("\n")
        self.output_buffer = lines.pop()
        for line in lines:
            if len(line) > 2:
                self.lines_output += 1
            wrapped_lines = textwrap.wrap(line, 450)
            for wrapped_line in wrapped_lines:
                m('irc_helpers').message(self.irc, self.channel, '~B[Z]~B %s' % wrapped_line)
    
    def save_game(self, filename):
        logger.debug("Stack: %s" % self.stack)
        logger.debug("Callstack: %s" % self.call_stack)
        QuetzalSaver("data/zmachine/saves/%s.sav" % filename.replace('/','_'), self)
        return True
    
    def load_game(self, filename):
        try:
            QuetzalLoader("data/zmachine/saves/%s.sav" % filename.replace('/','_'), self)
        except (IOError, QuetzalError), message:
            self.display_string("~BError loading file: %s~B\n" % message)
            return False
        return True
    
    def store(self, value):
        self.pc += 1
        variable = self.memory[self.pc]
        self.set_variable(variable, value)
    
    def branch(self, result):
        self.pc += 1
        branch = self.memory[self.pc]
        required_result = bool(branch & 0x80)
        target = branch & 0x3F
        
        if (branch & 0x40) == 0:
            target = target << 8
            self.pc += 1
            target |= self.memory[self.pc]
        
        target = self.sign(target, bits=14)
        
        if result == required_result:
            if target == 0:
                self.op_1op_b(0) # ret 0
            elif target == 1:
                self.op_1op_b(1) # ret 1
            else:
                self.pc += target - 2
    
    
    # Opcodes. :o
    
    # call
    def op_var_0(self, *args):
        args = list(args)
        routine = self.unpack_address(args.pop(0))
        if routine == 0:
            self.store(0)
            return
        varcount = self.memory[routine]
        if varcount > 15:
            raise StoryError, "Calling address %s without a routine!" % varcount
        self.pc += 1
        self.call_stack.append(((0x7F >> len(args)) << 8) | varcount) # Values needed for Quetzal saves.
        self.call_stack.append(self.memory[self.pc])
        self.call_stack.append(self.pc)
        self.call_stack.append(len(self.stack))
        for i in range(0, varcount):
            if args:
                self.stack.append(args.pop(0)) # Push argument onto the stack
            else:
                self.stack.append(self.unsigned_number(routine + i*2 +1)) # Push default value onto the stack
        
        self.pc = routine + varcount*2
    
    # storew
    def op_var_1(self, arr, word_index, value):
        self.set_number(arr + 2*word_index, value)
    
    # storeb
    def op_var_2(self, arr, byte_index, value):
        self.memory[arr + byte_index] = value
    
    # put_prop
    def op_var_3(self, obj, prop, value):
        address = self.get_object_property_address(obj, prop)
        size = self.get_property_size(obj, prop)
        if size == 1:
            self.memory[address] = value
        elif size == 2:
            self.set_number(address, value)
        else:
            raise StoryError, "Illegal put_prop on property of size greater than two."
    
    # read
    def op_var_4(self, text, parse):
        self.display_string("\n")
        self.input_wait.clear()
        self.awaiting_input = True
        self.input_wait.wait()
        if self.input_text is None:
        	return
        maxlength = self.memory[text] + 1
        read = self.input_text.lower()[0:maxlength]
        zscii = [ord(x) for x in read]
        self.memory[text+1:text+len(zscii)+1] = array('B',zscii)
        self.memory[text + len(zscii) + 1] = 0
        self.tokenise_zscii(parse, zscii)
    
    # print_char
    def op_var_5(self, character):
        self.print_string(self.zscii_to_ascii([character]))
    
    # print_num
    def op_var_6(self, value):
        self.print_string(str(value))
    
    # random
    def op_var_7(self, r):
        if r == 0:
            random.seed()
        elif r < 0:
            random.seed(r * -1)
        else:
            self.store(random.randint(1, r))
    
    # push
    def op_var_8(self, value):
        self.stack.append(value)
    
    # pull
    def op_var_9(self, variable):
        self.set_variable(variable, self.stack.pop())
    
    # split_window
    def op_var_a(self, lines):
        pass
    
    # set_window
    def op_var_b(self, lines):
        pass
    
    # output_stream
    def op_var_13(self, number, table=None):
        signed = self.sign(number)
        if signed > 4:
            number = self.sign(number, bits=8)
        else:
            number = signed
        
        if number == 1:
            self.stream_1 = True
        elif number == -1:
            self.stream_1 = False
        elif number == 2:
            self.stream_2 = True
            self.memory[0x10] |= 0x01 # See section 7.4
        elif number == -2:
            self.stream_2 = False
            self.memory[0x10] &= ~0x01 # See section 7.4
        elif number == 3:
            if len(self.stream_3) > 15:
                raise StoryError, "Can't have more than sixteen levels of stream 3!"
            if table is None:
                raise StoryError, "Must specify a table when opening stream 3"
            self.stream_3.append(table)
        elif number == -3:
            if len(self.stream_3) > 0:
                stream_3.pop()
        elif number == 4:
            self.stream_4 = True
        elif number == -4:
            self.stream_4 = False
        logger.warn("Attempted to set output stream to %s (unsupported)" % number)
    
    # input_stream
    def op_var_14(self, number):
        logger.warn("Attempted to set input stream to %s (unsupported)" % number)
    
    # rtrue
    def op_0op_0(self):
        self.op_1op_b(1) # ret 1
    
    # rfalse
    def op_0op_1(self):
        self.op_1op_b(0) # ret 0
    
    # print
    def op_0op_2(self):
        zchars = self.z_string(self.pc + 1)
        self.pc += (len(zchars) / 3) * 2
        zscii = self.zchar_to_zscii(zchars)
        ascii = self.zscii_to_ascii(zscii)
        self.print_string(ascii)
    
    # print_ret
    def op_0op_3(self):
        self.op_0op_2() # print
        self.op_0op_b() # new_line
        self.op_0op_0() # rtrue
    
    # nop
    def op_0op_4(self):
        pass # Useful, isn't it?
    
    # save
    def op_0op_5(self):
        self.display_string("Please enter a filename:\n")
        self.input_wait.clear()
        self.awaiting_input = True
        self.input_wait.wait()
        if not (self.input_text is None):
            success = self.save_game(self.input_text)
            self.branch(success)
    
    # restore
    def op_0op_6(self):
        self.display_string("Please enter a filename:\n")
        self.input_wait.clear()
        self.awaiting_input = True
        self.input_wait.wait()
        if not (self.input_text is None):
            success = self.load_game(self.input_text)
            self.branch(success)
    
    # restart
    def op_0op_7(self):
        # Re-initialise the VM, without re-entering the main loop.
        # Drop the program counter by one to counter increment at
        # the end of the loop
        self.run()
        self.pc -= 1
    
    # ret_popped
    def op_0op_8(self):
        self.op_1op_b(self.stack.pop())
    
    # pop
    def op_0op_9(self):
        self.stack.pop()
    
    # quit
    def op_0op_a(self):
        self.memory = None
        self.stack = None
        self.call_stack = None
        self.pc = 0
        self.output_buffer = ''
        self.display_string("~BVirtual machine terminated.~B\n")
        self.running = False
    
    # new_line
    def op_0op_b(self):
        self.display_string("\n")
    
    # set_status
    def op_0op_c(self):
        pass
    
    # verify
    def op_0op_d(self):
        # I'm lazy. Not going to bother to implement DRM.
        self.branch(True)
    
    # jz
    def op_1op_0(self, a):
        self.branch(a == 0)
    
    # get_sibling
    def op_1op_1(self, obj):
        sibling = self.get_object_sibling(obj)
        self.store(sibling)
        self.branch(sibling != 0)
    
    # get_child
    def op_1op_2(self, obj):
        child = self.get_object_child(obj)
        self.store(child)
        self.branch(child != 0)
    
    # get_parent
    def op_1op_3(self, obj):
        parent = self.get_object_parent(obj)
        self.store(parent)
    
    # get_prop_len
    def op_1op_4(self, address):
        if address == 0:
            self.store(0)
        else:
            self.store(self.get_property_size(address=address))
    
    # inc
    def op_1op_5(self, variable):
        value = self.get_variable(variable)
        value += 1
        self.set_variable(variable, value)
    
    # dec
    def op_1op_6(self, variable):
        value = self.get_variable(variable)
        value -= 1
        self.set_variable(variable, value)
    
    # print_addr
    def op_1op_7(self, address):
        zchars = self.z_string(address)
        zscii = self.zchar_to_zscii(zchars)
        ascii = self.zscii_to_ascii(zscii)
        self.print_string(ascii)
    
    # remove_obj
    def op_1op_9(self, obj):
        address = self.get_object_address(obj)
        previous_sibling = self.get_object_previous_sibling(obj)
        if previous_sibling == 0:
            parent = self.get_object_parent(obj)
            if parent > 0:
                parent_address = self.get_object_address(parent)
                if self.version < 4:
                    self.memory[parent_address + 6] = self.get_object_sibling(obj)
                else:
                    self.set_number(parent_address + 10, self.get_object_sibling(obj))
        else:
            previous_address = self.get_object_address(previous_sibling)
            self.memory[previous_address + 5] = self.memory[address + 5]
        self.memory[address + 5] = 0
        self.memory[address + 4] = 0
    
    # print_obj
    def op_1op_a(self, obj):
        self.print_string(self.zscii_to_ascii(self.zchar_to_zscii(self.get_object_name(obj))))
    
    # ret
    def op_1op_b(self, ret):
        stack_top = self.call_stack.pop()
        pc = self.call_stack.pop()
        var = self.call_stack.pop()
        self.call_stack.pop() # Useless bytes.
        self.stack = self.stack[0:stack_top]
        self.set_variable(var, ret)
        self.pc = pc
    
    # jump
    def op_1op_c(self, label):
        label = self.sign(label)
        self.pc += label - 2
    
    # print_paddr
    def op_1op_d(self, address):
        address = self.unpack_address(address)
        zchars = self.z_string(address)
        zscii = self.zchar_to_zscii(zchars)
        self.print_string(self.zscii_to_ascii(zscii))
    
    # load
    def op_1op_e(self, variable):
        self.store(self.get_variable(variable))
    
    # not
    def op_1op_f(self, value):
        self.store((~value) & 0xFFFF)
    
    # je (with two operands)
    def op_2op_1(self, a, b):
        self.branch(a == b)
    
    # jl
    def op_2op_2(self, a, b):
        self.branch(self.sign(a) < self.sign(b))
    
    # jg
    def op_2op_3(self, a, b):
        self.branch(self.sign(a) > self.sign(b))
    
    # dec_chk
    def op_2op_4(self, variable, value):
        var_value = self.get_variable(variable)
        var_value -= 1
        var_value &= 0xFFFF
        self.set_variable(variable, var_value)
        var_value = self.sign(var_value)
        value = self.sign(value)
        self.branch(var_value < value)
    
    # inc_chk
    def op_2op_5(self, variable, value):
        var_value = self.get_variable(variable)
        var_value += 1
        var_value &= 0xFFFF
        self.set_variable(variable, var_value)
        var_value = self.sign(var_value)
        value = self.sign(value)
        self.branch(var_value > value)
    
    # jin
    def op_2op_6(self, obj1, obj2):
        self.branch(self.get_object_parent(obj1) == obj2)
    
    # test
    def op_2op_7(self, bitmap, flags):
        self.branch((bitmap & flags) == flags)
    
    # or
    def op_2op_8(self, a, b):
        self.store(a | b)
    
    # and
    def op_2op_9(self, a, b):
        self.store(a & b)
    
    # test_attr
    def op_2op_a(self, obj, attr):
        self.branch(self.get_object_attribute(obj, attr))
    
    # set_attr
    def op_2op_b(self, obj, attr):
        self.set_object_attribute(obj, attr, True)
    
    # clear_attr
    def op_2op_c(self, obj, attr):
        self.set_object_attribute(obj, attr, False)
    
    # store
    def op_2op_d(self, variable, value):
        self.set_variable(variable, value)
    
    # insert_obj
    def op_2op_e(self, obj, destination):
        obj_addr = self.get_object_address(obj)
        dest_addr = self.get_object_address(destination)
        
        # The net aim of all of this is to move the object from one place to another.
        # This first part rebuilds the tree around its current position, jumping over it.
        previous_sibling = self.get_object_previous_sibling(obj)
        if previous_sibling == 0:
            # Set the child of the parent of the object to the sibling of the object
            self.memory[self.get_object_address(self.get_object_parent(obj)) + 6] = self.memory[obj_addr + 5]
        else:
            # Set the object that this object was a sibling of's sibling to the sibling of this object.
            self.memory[self.get_object_address(previous_sibling) + 5] = self.memory[obj_addr + 5]
        
        # This second part rebuilds the tree around its new position, including it
        # Set the sibling of the object to the child of the destination
        self.memory[obj_addr + 5] = self.memory[dest_addr + 6]
        # Set the child of the destination to the object
        self.memory[dest_addr + 6] = obj
        # Set the parent of the object to the destination
        self.memory[obj_addr + 4] = destination
    
    # loadw
    def op_2op_f(self, array, word_index):
        self.store(self.unsigned_number(array + word_index * 2))
    
    # loadb
    def op_2op_10(self, array, byte_index):
        self.store(self.memory[array + byte_index])
    
    # get_prop
    def op_2op_11(self, obj, prop):
        address = self.get_object_property_address(obj, prop)
        size = 2
        if address == 0:
            address = self.get_default_property_address(prop)
        else:
            size = (self.memory[address - 1] // 32) + 1
        if size == 1:
            self.store(self.memory[address])
        elif size == 2:
            self.store(self.unsigned_number(address))
    
    # get_prop_addr
    def op_2op_12(self, obj, prop):
        self.store(self.get_object_property_address(obj, prop))
    
    # get_next_prop
    def op_2op_13(self, obj, prop):
        if prop == 0:
            address = self.get_object_property_table_address(obj)
            address += self.memory[address] * 2 + 1
        else:
            address = self.get_object_property_address(obj, prop)
            address += self.memory[address - 1] // 32 + 1
        next_size_byte = self.memory[address]
        if address == 0:
            raise StoryError, "Illegal get_next_prop on nonexistent object property"
        if next_size_byte == 0:
            self.store(0)
        else:
            self.store(next_size_byte % 32)
    
    # add
    def op_2op_14(self, a, b):
        a = self.sign(a)
        b = self.sign(b)
        self.store(a + b)
    
    # sub
    def op_2op_15(self, a, b):
        a = self.sign(a)
        b = self.sign(b)
        self.store(a - b)
    
    # mul
    def op_2op_16(self, a, b):
        a = self.sign(a)
        b = self.sign(b)
        self.store(a * b)
    
    # div
    def op_2op_17(self, a, b):
        a = self.sign(a)
        b = self.sign(b)
        if b == 0:
            raise StoryError, "Division by zero!"
        self.store(a // b) # Integer division
    
    # div
    def op_2op_18(self, a, b):
        a = self.sign(a)
        b = self.sign(b)
        if b == 0:
            raise StoryError, "Modulo by zero!"
        self.store(a % b)
    
    # je (with three arguments)
    def op_3op_1(self, a, b, c):
        self.branch(a == b or a == c)
    
    # je (with four arguments)
    def op_4op_1(self, a, b, c, d):
        self.branch(a == b or a == c or a == d)

class QuetzalSaver(object):
    machine = None
    original_image = None
    
    def __init__(self, save_file, machine):
        self.machine = machine
        o = open(self.machine.story, 'rb')
        self.original_image = array('B')
        try:
            self.original_image.fromfile(o, self.machine.memory_dynamic_end)
        except EOFError:
            pass
        o.close()
        self.write_save(save_file)
    
    def write_save(self, filename):
        f = open(filename, 'wb')
        s = StringIO.StringIO()
        self.write_IFhd(s)
        if COMPRESS_SAVE_FILES:
            self.write_CMem(s)
        else:
            self.write_UMem(s)
        self.write_Stks(s)
        self.write_ANNO(s)
        self.write_AUTH(s)
        form = s.getvalue()
        s.close()
        f.write('FORM%sIFZS%s' % (struct.pack('!I', len(form) + 4), form))
        f.close()
    
    def write_IFhd(self, stream):
        args = []
        args.append(13)
        args.append(self.machine.unsigned_number(0x02))
        args.extend(self.machine.memory[0x12:0x18])
        args.append(self.machine.unsigned_number(0x1C))
        pc = self.machine.pc + 1
        args.extend(((pc >> 16) & 0xFF, (pc >> 8) & 0xFF, pc & 0xFF))
        stream.write('IFhd%s' % struct.pack('!IH6BH3B', *args))
        stream.write('\x00')
    
    def write_CMem(self, stream):
        cmem = array('B')
        running = False
        run = 0
        for i in xrange(0, self.machine.memory_dynamic_end):
            xor = self.original_image[i] ^ self.machine.memory[i]
            if xor != 0:
                if running:
                    running = False
                    cmem.append(run)
                cmem.append(xor)
            else:
                if running:
                    run += 1
                    if run > 255:
                        cmem.append(255)
                        cmem.append(0)
                        run = 0
                else:
                    cmem.append(0)
                    running = True
                    run = 0
        
        if running:
            cmem.append(run)
        
        stream.write('CMem%s%s' % (struct.pack('!I', len(cmem)), cmem.tostring()))
        if len(cmem) % 2 == 1:
            stream.write('\x00')
    
    def write_UMem(self, stream):
        umem = self.machine.memory[0:self.machine.memory_dynamic_end]
        stream.write('UMem%s%s' % (struct.pack('!I', len(umem)), umem.tostring()))
        if len(umem) % 2 == 1:
            stream.write('\x00')
    
    def write_Stks(self, stream):
        callstack_pointer = 0
        stack_pointer = 0
        chunk_length = 0
        frame_stream = StringIO.StringIO()
        
        # Dummy first frame
        args = [0,0,0,0,0,0]
        if len(self.machine.call_stack) > 3:
            eval_count = self.machine.call_stack[3]
        else:
            eval_count = 0
        args.append(eval_count)
        args.extend(self.machine.stack[0:eval_count])
        frame_stream.write(struct.pack('!3BBBBH%iH' % eval_count, *args))
        chunk_length += 8 + eval_count*2
        
        while callstack_pointer < len(self.machine.call_stack):
            args_supplied = self.machine.call_stack[callstack_pointer] >> 8
            local_count = self.machine.call_stack[callstack_pointer] & 0x0F
            ret_var = self.machine.call_stack[callstack_pointer + 1]
            pc = self.machine.call_stack[callstack_pointer + 2]
            top = self.machine.call_stack[callstack_pointer + 3]
            callstack_pointer += 4
            if callstack_pointer + 3 >= len(self.machine.call_stack):
                eval_count = len(self.machine.stack) - top
            else:
                eval_count = self.machine.call_stack[callstack_pointer + 3] - top
            eval_count -= local_count
            
            pc += 1 # Counter for our disagreement with the beginning of pc
            
            chunk_length += 8 + local_count*2 + eval_count*2
            
            # Write frame
            args = []
            args.extend(((pc >> 16) & 0xFF, (pc >> 8) & 0xFF, pc & 0xFF))
            args.append(local_count) # We can ignore "p" because the call_xN ops don't exist
            args.append(ret_var)
            args.append(args_supplied)
            args.append(eval_count)
            args.extend(self.machine.stack[top:top+local_count])
            args.extend(self.machine.stack[top+local_count:top+local_count+eval_count])
            
            frame_stream.write(struct.pack('!3BBBBH%iH%iH' % (local_count, eval_count), *args))
        
        stream.write("Stks%s%s" % (struct.pack('!I', chunk_length), frame_stream.getvalue()))
        if chunk_length % 2 == 1:
            stream.write('\x00')
        frame_stream.close()
    
    def write_ANNO(self, stream):
        message = "Version %s game, saved by KathBot3 @%s" % (self.machine.version, datetime.datetime.now())
        stream.write("ANNO%s%s" % (struct.pack('!I', len(message)), message))
        
        if len(message) % 2 == 1:
            stream.write('\x00')
    
    def write_AUTH(self, stream):
        message = "The members of %s on %s" % (self.machine.channel, self.machine.irc.network.server)
        stream.write("AUTH%s%s" % (struct.pack('!I', len(message)), message))
        
        if len(message) % 2 == 1:
            stream.write('\x00')

class QuetzalLoader(object):
    machine = None
    
    def __init__(self, save_file, machine):
        f = open(save_file, 'rb')
        form = Chunk(f)
        self.machine = machine
        if form.read(4) != 'IFZS':
            raise QuetzalError, "File is not a quetzal save file!"
        
        # Read the thing
        while True:
            try:
                chunk = Chunk(form)
            except EOFError:
                break
            function = "chunk_%s" % chunk.getname().strip()
            if hasattr(self, function):
                self.__getattribute__(function)(chunk)
    
    def chunk_IFhd(self, chunk):
        ifhd = struct.unpack('!H6BH3B', chunk.read())
        release = ifhd[0]
        serial = array('B', ifhd[1:7])
        checksum = ifhd[7]
        pc = (ifhd[8] << 16) | (ifhd[9] << 8) | ifhd[10]
        if self.machine.unsigned_number(0x02) != release or \
            self.machine.memory[0x12:0x18] != serial or \
            checksum != self.machine.unsigned_number(0x1C):
            raise QuetzalError, "Wrong game!"
        
        self.machine.load_story()
        self.machine.pc = pc - 1
    
    def chunk_CMem(self, chunk):
        cmem = array('B', chunk.read())
        pointer = 0
        skipping = False
        for byte in cmem:
            if byte != 0 and not skipping:
                self.machine.memory[pointer] ^= byte
                pointer += 1
            elif not skipping:
                skipping = True
                pointer += 1
            else:
                skipping = False
                pointer += byte
        
        if skipping:
            raise QuetzalError, "Bad save data!"
        if pointer > self.machine.memory_dynamic_end:
            raise QuetzalError, "Save data overruns dynamic memory area"
    
    def chunk_UMem(self, chunk):
        umem = array('B', chunk.read())
        if len(umem) != self.machine.memory_dynamic_end:
            raise QuetzalError, "Uncompressed memory image is the wrong size!"
        self.machine.memory[0:self.machine.memory_dynamic_end] = umem
    
    def chunk_Stks(self, chunk):
        self.machine.stack = array('H')
        self.machine.call_stack = array('I')
        while True:
            pc = chunk.read(3)
            if pc == '':
                break
            if len(pc) != 3:
                raise QuetzalError, "Something bad happened!"
            pc = struct.unpack('!3B', pc)
            pc = (pc[0] << 16) | (pc[1] << 8) | pc[2]
            flags = struct.unpack('!B', chunk.read(1))[0]
            discard_result = flags & 0x10
            local_count = flags & 0x0F
            ret_var = struct.unpack('!B', chunk.read(1))[0]
            args_supplied = struct.unpack('!B', chunk.read(1))[0]
            stack_size = struct.unpack('!H', chunk.read(2))[0]
            local = struct.unpack('!%iH' % local_count, chunk.read(local_count * 2))
            stack = struct.unpack('!%iH' % stack_size, chunk.read(stack_size * 2))
            
            # Actually put the data on.
            if pc > 0:
                self.machine.call_stack.append((args_supplied << 8) | local_count)
                self.machine.call_stack.append(ret_var)
                self.machine.call_stack.append(pc - 1)
                self.machine.call_stack.append(len(self.machine.stack))
            for var in local:
                self.machine.stack.append(var)
            for word in stack:
                self.machine.stack.append(word)
        logger.debug("Loaded: stack: %s" % self.machine.stack)
        logger.debug("Loaded: callstack: %s" % self.machine.call_stack)
    
    def chunk_ANNO(self, chunk):
        message = chunk.read()
        self.machine.display_string("~BSave file information~B: %s\n" % message)
    
    def chunk_AUTH(self, chunk):
        message = chunk.read()
        self.machine.display_string("~BSave file creator~B: %s\n" % message)

z_machines = {}

def process_machine_message(network, channel, message):
    z_machine = z_machines.get("%s/%s" % (network, channel))
    if not z_machine:
        logger.info("Discarded unwanted message to z-machine %s/%s" % (network, channel))
        return
    if z_machine.awaiting_input:
        z_machine.input_text = message.strip()
        z_machine.input_wait.set()
    else:
        logger.info("Z-Machine didn't want input.")

def terminate_machine(network, channel):
    machine = "%s/%s" % (network, channel)
    z_machine = z_machines.get(machine)
    if not z_machine:
        return
    logger.info("Shutting down %s..." % (machine))
    z_machine.running = False
    if z_machine.awaiting_input:
        logger.info("Stopping input wait.")
        z_machine.input_text = None
        z_machine.input_wait.set()
    logger.info("Waiting for shutdown to complete...")
    z_machine.join()
    logger.info("Shut down %s sucessfully." % (machine))

def launch_machine(irc, channel, story):
    z_machine = ZMachine(irc, channel, story)
    machine = "%s/%s" % (irc.network.name, channel)
    z_machines[machine] = z_machine
    z_machine.start()
    logger.info("Launched new z-machine")

def init():
    add_hook('privmsg', privmsg)

def privmsg(irc, origin, args):
    irc_helpers = m('irc_helpers')
    target, command, args = irc_helpers.parse(args)
    if command == 'zdo':
        message = ' '.join(args)
        process_machine_message(irc.network.name, target, message)
    elif command == 'zload':
        try:
            terminate_machine(irc.network.name, target)
            launch_machine(irc, target, args[0])
        except Exception, message:
            irc_helpers.message(irc, target, "Error launching Z-Machine: %s" % message)
        

def shutdown():
    logger.info("Shutting down all Z-Machines.")
    for machine in z_machines:
        z_machine = z_machines[machine]
        z_machine.running = False
        if z_machine.awaiting_input:
            z_machine.input_text = None
            z_machine.input_wait.set()
        z_machines[machine].join()
        logger.info("Shut down %s sucessfully." % (machine))
    logger.info("Z-Machine shutdown complete.")
