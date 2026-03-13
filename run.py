import subprocess
import time


def main():
    # Ollama call
    ollama_proc = subprocess.Popen(["ollama", "serve"])

    try:
        time.sleep(2)
        subprocess.run(["python", "main.py"], check=True)
    finally:
        ollama_proc.terminate()

if __name__ == "__main__":
    main()