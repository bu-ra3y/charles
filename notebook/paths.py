import sys
from pathlib import Path

# With Project directory structure like:
# src: https://stackoverflow.com/a/38288353
# Project/
#   src/
#     mymodule.py
#     mypackage/
#         __init__.py
#
#   notebooks/
#     mynb.ipynb
#     mynb2.ipynb
#     paths.py     <--- us, here
#
# we want to get the path of src/
path = Path(__file__).parent.parent
print(f"Adding to path: {path}. You can now import thoron code as usual, like:\n"
      f"from thoron.qgis import QgisTiff")

# set it as the first place to look
sys.path.insert(0, str(path))
