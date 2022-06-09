import numpy as np
import librosa
import midiutil


# class to convert WAV file to MIDI file
class WavToMidi:
    """
        Returns the transition matrix with one silence state and two states
        (onset and sustain) for each note.
        Parameters
        ----------
        minimum_note : string, 'A#4' format
            Lowest note supported by this transition matrix
        max_note : string, 'A#4' format
            Highest note supported by this transition matrix
        p_stay_note : float, between 0 and 1
            Probability of a sustain state returning to itself.
        p_stay_silence : float, between 0 and 1
            Probability of the silence state returning to itself.
        Returns
        -------
        a 2x2 Trasition matrix in which T[i,j] is the probability of
            going from state i to state j
    """
    @staticmethod
    def build_transition_matrix(minimum_note, max_note, p_stay_note, p_stay_silence):

        midi_min = librosa.note_to_midi(minimum_note)
        midi_max = librosa.note_to_midi(max_note)
        n_notes = midi_max - midi_min + 1
        p_ = (1 - p_stay_silence) / n_notes
        p__ = (1 - p_stay_note) / (n_notes + 1)

        # Transition matrix:
        # State 0 = silence
        # States 1, 3, 5... = onsets
        # States 2, 4, 6... = sustains
        np_matrix = np.zeros((2 * n_notes + 1, 2 * n_notes + 1))

        # State 0: silence
        np_matrix[0, 0] = p_stay_silence
        for i in range(n_notes):
            np_matrix[0, (i * 2) + 1] = p_

        # States 1, 3, 5... = onsets
        for i in range(n_notes):
            np_matrix[(i * 2) + 1, (i * 2) + 2] = 1

        # States 2, 4, 6... = sustains
        for i in range(n_notes):
            np_matrix[(i * 2) + 2, 0] = p__
            np_matrix[(i * 2) + 2, (i * 2) + 2] = p_stay_note
            for j in range(n_notes):
                np_matrix[(i * 2) + 2, (j * 2) + 1] = p__

        return np_matrix

    """
        Estimate prior (observed) probabilities from audio signal

        Parameters
        ----------
        y : 1-D numpy array containing audio samples
        minimum_note : string, 'A#4' format
            Lowest note supported by this estimator
        max_note : string, 'A#4' format
            Highest note supported by this estimator
        sr : int
            Sample rate.
        frame_length : int
        window_length : int
        hop_length : int
            Parameters for FFT estimation
        pitch_acc : float, between 0 and 1
            Probability (estimated) that the pitch estimator is correct.
        voiced_acc : float, between 0 and 1
            Estimated accuracy of the "voiced" parameter.
        onset_acc : float, between 0 and 1
            Estimated accuracy of the onset detector.
        spread : float, between 0 and 1
            Probability that the singer/musician had a one-semitone deviation
            due to vibrato or glissando.
        Returns
        -------
        2D array where P[j,t] is the prior probability of being in state j at time t.
    """
    @staticmethod
    def calc_probabilities(y, minimum_note, max_note, sr, frame_length, window_length, hop_length,
                           pitch_acc, voiced_acc, onset_acc, spread):
        fmin = librosa.note_to_hz(minimum_note)
        fmax = librosa.note_to_hz(max_note)
        midi_min = librosa.note_to_midi(minimum_note)
        midi_max = librosa.note_to_midi(max_note)
        n_notes = midi_max - midi_min + 1

        # F0 and voicing
        f0, voiced_flag, voiced_prob = librosa.pyin(y, fmin * 0.9, fmax * 1.1, sr, frame_length, window_length, hop_length)
        tuning = librosa.pitch_tuning(f0)
        f0_ = np.round(librosa.hz_to_midi(f0 - tuning)).astype(int)
        onsets = librosa.onset.onset_detect(y, sr=sr, hop_length=hop_length, backtrack=True)

        P = np.ones((n_notes * 2 + 1, len(f0)))

        for t in range(len(f0)):
            # probability of silence or onset = 1-voiced_prob
            # Probability of a note = voiced_prob * (pitch_acc) (estimated note)
            # Probability of a note = voiced_prob * (1-pitch_acc) (estimated note)
            if voiced_flag[t] == False:
                P[0, t] = voiced_acc
            else:
                P[0, t] = 1 - voiced_acc

            for j in range(n_notes):
                if t in onsets:
                    P[(j * 2) + 1, t] = onset_acc
                else:
                    P[(j * 2) + 1, t] = 1 - onset_acc

                if j + midi_min == f0_[t]:
                    P[(j * 2) + 2, t] = pitch_acc

                elif np.abs(j + midi_min - f0_[t]) == 1:
                    P[(j * 2) + 2, t] = pitch_acc * spread

                else:
                    P[(j * 2) + 2, t] = 1 - pitch_acc

        return P

    """
        Converts state sequence to an intermediate, internal piano-roll notation
        Parameters
        ----------
        states : int
            Sequence of states estimated by Viterbi
        minimum_note : string, 'A#4' format
            Lowest note supported by this estimator
        max_note : string, 'A#4' format
            Highest note supported by this estimator
        hop_time : float
            Time interval between two states.
        Returns
        -------
        output : List of lists
            output[i] is the i-th note in the sequence. Each note is a list
            described by [onset_time, offset_time, pitch].
    """
    @staticmethod
    def convert_states_to_pianoroll(states, minimum_note, max_note, hop_time):
        midi_min = librosa.note_to_midi(minimum_note)
        midi_max = librosa.note_to_midi(max_note)

        states_ = np.hstack((states, np.zeros(1)))

        # possible types of states
        silence = 0
        onset = 1
        sustain = 2

        my_state = silence
        output = []

        last_onset = 0
        last_offset = 0
        last_midi = 0
        for i in range(len(states_)):
            if my_state == silence:
                if int(states_[i] % 2) != 0:
                    # Found an onset!
                    last_onset = i * hop_time
                    last_midi = ((states_[i] - 1) / 2) + midi_min
                    last_note = librosa.midi_to_note(last_midi)
                    my_state = onset


            elif my_state == onset:
                if int(states_[i] % 2) == 0:
                    my_state = sustain

            elif my_state == sustain:
                if int(states_[i] % 2) != 0:
                    # Found an onset.
                    # Finish last note
                    last_offset = i * hop_time
                    my_note = [last_onset, last_offset, last_midi, last_note]
                    output.append(my_note)

                    # Start new note
                    last_onset = i * hop_time
                    last_midi = ((states_[i] - 1) / 2) + midi_min
                    last_note = librosa.midi_to_note(last_midi)
                    my_state = onset

                elif states_[i] == 0:
                    # Found silence. Finish last note.
                    last_offset = i * hop_time
                    my_note = [last_onset, last_offset, last_midi, last_note]
                    output.append(my_note)
                    my_state = silence

        return output

    """
        Parameters
        ----------
        1D numpy array containing audio signal (used to estimate BPM)
        A pianoroll list as estimated by states_to_pianoroll function.
    """
    @staticmethod
    def convert_pianoroll_to_midi(y, pianoroll):
        bpm = librosa.beat.tempo(y)[0]
        # print(bpm)
        quarter_note = 60 / bpm
        ticks_per_quarter = 1024

        onsets = np.array([p[0] for p in pianoroll])
        offsets = np.array([p[1] for p in pianoroll])

        onsets = onsets / quarter_note
        offsets = offsets / quarter_note
        durations = offsets - onsets

        MyMIDI = midiutil.MIDIFile(1)
        MyMIDI.addTempo(0, 0, bpm)

        for i in range(len(onsets)):
            MyMIDI.addNote(0, 0, int(pianoroll[i][2]), onsets[i], durations[i], 100)

        return MyMIDI

    # base method to convert wav file to midi format
    @staticmethod
    def convert_file(file_in, file_out):
        minimum_note = 'A2'
        max_note = 'E6'
        voiced_acc = 0.9
        onset_acc = 0.8
        frame_length = 2048
        window_length = 1024
        hop_length = 256
        pitch_acc = 0.99
        spread = 0.6

        y, sr = librosa.load(file_in)

        tran_matrix = WavToMidi.build_transition_matrix(minimum_note, max_note, 0.9, 0.2)
        prob = WavToMidi.calc_probabilities(y, minimum_note, max_note, sr, frame_length, window_length,
                                    hop_length, pitch_acc, voiced_acc, onset_acc, spread)
        init_mat = np.zeros(tran_matrix.shape[0])
        init_mat[0] = 1

        states = librosa.sequence.viterbi(prob, tran_matrix, p_init=init_mat)
        # print(states)
        piano_format = WavToMidi.convert_states_to_pianoroll(states, minimum_note, max_note, hop_length / sr)
        # print(pianoroll)
        midi_format = WavToMidi.convert_pianoroll_to_midi(y, piano_format)
        with open(file_out, "wb") as output_file:
            midi_format.writeFile(output_file)
