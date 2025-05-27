import obspython as obs
import os
import datetime
import time
import subprocess
import math

# Global state
log_file_path = os.path.join(os.environ['USERPROFILE'], "scene_changes.log")
recording_active = False
recording_start_time = None
scene_filter = []  # List of scenes to log
inscene = False
mkvmerge_path = None


# Logging function
def log_scene_change(scene_name, elapsed_time):
    global inscene
    print("nominal time: "+ str(datetime.timedelta(seconds =elapsed_time)))
    if (inscene): #subtract transition if moving into the scene
        timestamp = elapsed_time-obs.obs_frontend_get_transition_duration()/1000
    else: #add transition if moving out of the scene
        timestamp = elapsed_time+obs.obs_frontend_get_transition_duration()/1000  
    print("corrected time: "+ str(datetime.timedelta(seconds =timestamp)))
    with open(log_file_path, "a") as f:
        f.write(f"{datetime.timedelta(seconds =timestamp)},")

# Get recording elapsed time
def get_recording_elapsed_time():
    if recording_active and recording_start_time:
        return time.monotonic() - recording_start_time        
    return None

# Scene changed or recording started/stopped
def on_event(event):
    global recording_active, recording_start_time, inscene, mkvmerge_path

    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
        
        recording_active = True
        with open(log_file_path,"w") as f:
            f.write("")
        if  obs.obs_source_get_name(obs.obs_frontend_get_current_scene()) in scene_filter :
            inscene = True
            
            
        recording_start_time = time.monotonic()

    elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        recording_active = False
        recording_start_time = None
        recording_name = obs.obs_frontend_get_last_recording()
        output_name=recording_name[:recording_name.rindex('.')]

        with open(log_file_path,"r") as f:
            splitstring = f.read()
            splitstring=splitstring[:splitstring.rindex(',')]
        
        
        if mkvmerge_path is not None and "," in splitstring: 
            print(splitstring)
            subprocess.run(str(mkvmerge_path)+" -o " +"\""+ output_name  +"-.mkv" +"\"" + " --split timestamps:" + splitstring +" \"" + recording_name +"\"")

    elif event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED:
        if recording_active:
            current_scene = obs.obs_frontend_get_current_scene()
            if current_scene:
                scene_name = obs.obs_source_get_name(current_scene)
                if inscene: 
                    log_scene_change(scene_name, get_recording_elapsed_time())
                    inscene=False
                elif scene_name in scene_filter:
                    elapsed = get_recording_elapsed_time()
                    if elapsed:
                        inscene=True
                        log_scene_change(scene_name, elapsed)
                obs.obs_source_release(current_scene)

# OBS UI: Script description
def script_description():
    return "Logs timestamps of selected scene changes during active recording and then uses mkvmerge to split the recorded file.\nBy: FFyte" 
    

# OBS UI: Create properties
def script_properties():
    props = obs.obs_properties_create()
    
    filt= ""
    defaultpath = "."
    p = obs.obs_properties_add_path(props,"mkvmerge_path","Path to mkvmerge",obs.OBS_PATH_FILE,filt,defaultpath)
    #p= obs.obs_properties_add_text(props, "Duration","The current fade duration to the timestamp: "+str(obs.obs_frontend_get_transition_duration()/1000),obs.OBS_TEXT_INFO)
    p= obs.obs_properties_add_text(props, "Selected_scenes","Select the scenes to include:",obs.OBS_TEXT_INFO)
    scenes = get_scene_names()
    if scenes:
        
        for s in scenes:
            p = obs.obs_properties_add_bool(props,s,s)

    
    return props

# OBS UI: Handle property updates
def script_update(settings):
    global scene_filter,mkvmerge_path
    scene_filter.clear()
    for s in get_scene_names():
        if obs.obs_data_get_bool(settings,s): scene_filter.append(s)
    mkvmerge_path=obs.obs_data_get_string(settings,"mkvmerge_path")
    
# Load script
def script_load(settings):
    obs.obs_frontend_add_event_callback(on_event)
    print(str(datetime.datetime.now()) +" loaded script")

# Get available scenes
def get_scene_names():
    scenes = []
    sources2 = []
    sources = obs.obs_frontend_get_scenes(sources2)
    
    if sources is not None:
        for source in sources:
            if obs.obs_source_get_type(source) == obs.OBS_SOURCE_TYPE_SCENE:
                scenes.append(obs.obs_source_get_name(source))
    else: 
        print("no sources")
    return scenes
