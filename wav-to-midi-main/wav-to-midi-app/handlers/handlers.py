from businesslogic.wav_to_midi import WavToMidi


# handler to call the convert logic
class Convert:

    # constructor
    def __int__(self):
        return

    # handler caller method for the wav to midi converter
    @staticmethod
    def convert_file(source_file_name, target_file_name):
        WavToMidi.convert_file(source_file_name, target_file_name)
