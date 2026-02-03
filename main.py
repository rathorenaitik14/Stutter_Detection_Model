import whisper
import jiwer
import pyaudio
import wave
import threading
import os
import re  # Import regex for better text cleaning
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# --- GLOBAL SETTINGS ---
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
frames = []
is_recording = False

def record_audio(filename):
    """
    Runs in a background thread. Records audio continuously.
    """
    global is_recording, frames
    p = pyaudio.PyAudio()
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print(f"{Fore.GREEN}>>> RECORDING... (Read the text now!) <<<{Style.RESET_ALL}")
    
    frames = [] # Reset buffer
    while is_recording:
        data = stream.read(CHUNK)
        frames.append(data)

    print(f"{Fore.CYAN}Processing audio...{Style.RESET_ALL}")
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def clean_text(text):
    """
    Cleans text by removing punctuation and ensuring words are separated.
    """
    # 1. Replace punctuation with a space (prevents "town.A" -> "towna")
    text = text.replace(".", " ").replace(",", " ").replace("!", " ").replace("?", " ")
    
    # 2. Lowercase
    text = text.lower()
    
    # 3. Remove extra spaces (e.g., "town  a" -> "town a")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def analyze_stutter(reference_text, audio_path):
    print(f"{Fore.CYAN}Loading Whisper model...{Style.RESET_ALL}")
    model = whisper.load_model("base")

    # Transcribe
    try:
        result = model.transcribe(audio_path, fp16=False)
        transcript = result["text"]
    except Exception as e:
        print(f"{Fore.RED}Error during transcription: {e}{Style.RESET_ALL}")
        return

    print(f"\n{Fore.YELLOW}Reference :{Style.RESET_ALL} {reference_text}")
    print(f"{Fore.YELLOW}Transcript:{Style.RESET_ALL} {transcript}\n")

    # --- FIX APPLIED HERE ---
    ref_norm = clean_text(reference_text)
    hyp_norm = clean_text(transcript)
    
    # Split reference into a list so we can find words by index later
    ref_words = ref_norm.split()

    # Alignment
    output = jiwer.process_words(ref_norm, hyp_norm)
    alignment = output.alignments[0]
    
    # Trackers for the Report
    correct_count = 0
    stuttered_words_debug = []     # For the detailed breakdown
    mispronounced_words_debug = [] # For the detailed breakdown
    skipped_words_debug = []       # For the detailed breakdown
    
    # NEW LIST: The specific words the user struggled with
    words_struggled_with = []
    
    print(f"{Fore.BLUE}--- Visualization ---{Style.RESET_ALL}\n")
    
    for op in alignment:
        ref_chunk = ref_norm.split()[op.ref_start_idx:op.ref_end_idx]
        hyp_chunk = hyp_norm.split()[op.hyp_start_idx:op.hyp_end_idx]

        if op.type == 'equal':
            print(f"{Fore.GREEN}{' '.join(hyp_chunk)} ", end="")
            correct_count += len(hyp_chunk)
            
        elif op.type == 'substitute':
            print(f"{Fore.RED}[SUB: {' '.join(hyp_chunk)}] ", end="")
            mispronounced_words_debug.append(f"Expected '{' '.join(ref_chunk)}' but said '{' '.join(hyp_chunk)}'")
            
            # Logic: If substituted, the user struggled with the Reference Word
            for w in ref_chunk:
                words_struggled_with.append(w)
            
        elif op.type == 'insert':
            print(f"{Fore.RED}[STUTTER: {' '.join(hyp_chunk)}] ", end="")
            stuttered_words_debug.append(f"Inserted/Stuttered: '{' '.join(hyp_chunk)}'")
            
            # Logic: If inserted, check the upcoming word in reference
            if op.ref_start_idx < len(ref_words):
                next_word = ref_words[op.ref_start_idx]
                words_struggled_with.append(next_word)
            
        elif op.type == 'delete':
            print(f"{Fore.RED}[SKIPPED: {' '.join(ref_chunk)}] ", end="")
            skipped_words_debug.append(f"Skipped: '{' '.join(ref_chunk)}'")

    # --- CALCULATION LOGIC ---
    total_spoken_words = len(hyp_norm.split())
    
    if total_spoken_words > 0:
        fluency_score = (correct_count / total_spoken_words) * 100
    else:
        fluency_score = 0

    print("\n\n" + "="*40)
    print(f"      {Fore.MAGENTA}FLUENCY SCORE: {int(fluency_score)}/100{Style.RESET_ALL}")
    print("="*40)

    # --- NEW SECTION: CONSOLIDATED LIST ---
    print(f"\n{Fore.CYAN}--- Words You Struggled With ---{Style.RESET_ALL}")
    if words_struggled_with:
        # Remove duplicates while preserving order
        seen = set()
        unique_struggles = [x for x in words_struggled_with if not (x in seen or seen.add(x))]
        
        print("These are the words where you stuttered, repeated, or fumbled just before:")
        print(f"{Fore.YELLOW}{unique_struggles}{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}None! Clean reading.{Style.RESET_ALL}")

    print(f"\n{Fore.RED}--- Detailed Error Report ---{Style.RESET_ALL}")
    
    if not (stuttered_words_debug or mispronounced_words_debug or skipped_words_debug):
        print(f"{Fore.GREEN}Perfect reading! No errors detected.{Style.RESET_ALL}")
    else:
        if stuttered_words_debug:
            print(f"\n{Fore.YELLOW}Extra Sounds / Repetitions:{Style.RESET_ALL}")
            for w in stuttered_words_debug: print(f"  - {w}")
            
        if mispronounced_words_debug:
            print(f"\n{Fore.YELLOW}Mispronunciations:{Style.RESET_ALL}")
            for w in mispronounced_words_debug: print(f"  - {w}")

        if skipped_words_debug:
            print(f"\n{Fore.YELLOW}Skipped Words:{Style.RESET_ALL}")
            for w in skipped_words_debug: print(f"  - {w}")
    
    print("-" * 40)

# --- MAIN APP FLOW ---
if __name__ == "__main__":
    target_text = "The sun rose slowly over the quiet town.A small bird hopped quickly across the path.Cool rain fell softly on the empty street."
    
    temp_filename = "manual_record.wav"
    
    print("-" * 50)
    print(f"TEXT TO READ:\n")
    print(f"{Fore.WHITE}{Style.BRIGHT}{target_text}{Style.RESET_ALL}\n")
    print("-" * 50)
    
    # 1. Start Recording
    input(f"Press {Fore.GREEN}ENTER{Style.RESET_ALL} to START recording...")
    is_recording = True
    
    record_thread = threading.Thread(target=record_audio, args=(temp_filename,))
    record_thread.start()
    
    # 2. Stop Recording
    input(f"Press {Fore.RED}ENTER{Style.RESET_ALL} again to STOP recording...")
    is_recording = False
    
    record_thread.join()
    
    # 3. Analyze
    if os.path.exists(temp_filename):
        analyze_stutter(target_text, temp_filename)