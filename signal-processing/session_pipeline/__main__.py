import argparse
from .pipeline import process, save_result


def main():
    parser=argparse.ArgumentParser(description='Process a stopped v0 recording locally. Does not upload.')
    parser.add_argument('csv')
    parser.add_argument('--metadata')
    parser.add_argument('--patient-id',required=True)
    parser.add_argument('--exercise',default='bicep_curl',choices=['bicep_curl'])
    parser.add_argument('--side',required=True,choices=['left','right'])
    parser.add_argument('--axis',choices=['x','y','z'])
    parser.add_argument('--ppg-channel',default='ppg_green',choices=['ppg_green','ppg_red','ppg_infrared','ppg_blue'])
    parser.add_argument('--rep-goal',type=int)
    parser.add_argument('--max-hr-bpm',type=float)
    parser.add_argument('--output',required=True)
    parser.add_argument('--experimental-model',help='Trusted local legacy Isolation Forest file; enables experimental predictions')
    parser.add_argument('--experimental-scaler',help='Matching trusted local scaler file')
    args=parser.parse_args()
    try:
        result=process(args.csv,metadata_path=args.metadata,patient_id=args.patient_id,
                       exercise_id=args.exercise,body_side=args.side,axis=args.axis,
                       ppg_channel=args.ppg_channel,rep_goal=args.rep_goal,max_hr_bpm=args.max_hr_bpm,
                       experimental_model=args.experimental_model,experimental_scaler=args.experimental_scaler)
        save_result(result,args.output)
    except (ValueError,OSError,KeyError) as exc:
        parser.exit(2,f'Could not process recording: {exc}\n')
    print(f"Saved {args.output}\nEstimated reps: {result['imu']['accepted_reps']}\n"
          f"Pulse estimate: {result['hr']['bpm']}\nPatient state: {result['guidance']['patient_state']}")

if __name__=='__main__':main()
