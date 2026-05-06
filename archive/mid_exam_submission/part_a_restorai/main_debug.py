import sys
import traceback
import os
os.environ["CHROMA_TELEMETRY_IMPL"] = "None"
sys.argv = ['main.py', '--mode', 'demo']

try:
    import main
    main.main()
except Exception as e:
    print("FATAL ERROR CAUGHT")
    traceback.print_exc()
