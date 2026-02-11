import os
import shutil

def save_file(buffer, filename):
    file_path = os.path.join("uploads", filename)
    with open(file_path, "wb") as file_buffer:
        shutil.copyfileobj(buffer, file_buffer)
        return file_path

# Usage example:
# save_file(department_kpi.file, DEPARTMENT_KPI_PATH, department_kpi.filename)