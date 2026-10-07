"""Version-matched scoring process for trusted local REHAB artifacts."""
import sys,json,pickle,hashlib,warnings
from pathlib import Path
import numpy as np
import sklearn
from sklearn.exceptions import InconsistentVersionWarning

def main():
    request=json.load(sys.stdin);directory=Path(request['model_directory']).resolve()
    if directory.parent!=Path(__file__).resolve().parent/'models':raise ValueError('Expected a local exercise model directory.')
    config=json.loads((directory/'feature_config.json').read_text());meta=json.loads((directory/'metadata.json').read_text())
    if sklearn.__version__!=meta['versions']['scikit_learn']:raise ValueError('Model training/runtime sklearn versions differ.')
    artifacts=[]
    for name in [config['exercise_name']+'_isolation_forest.pkl','scaler.pkl']:
        data=(directory/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=meta['artifact_sha256'][name]:raise ValueError('Model artifact hash mismatch.')
        with warnings.catch_warnings():
            warnings.simplefilter('error',InconsistentVersionWarning);artifacts.append(pickle.loads(data))
    model,scaler=artifacts;x=np.asarray(request['features'],dtype=float)
    if x.ndim!=2 or x.shape[1]!=len(config['feature_columns']) or not np.isfinite(x).all():raise ValueError('Invalid feature matrix.')
    if model.n_features_in_!=x.shape[1] or scaler.n_features_in_!=x.shape[1]:raise ValueError('Model feature count mismatch.')
    scores=-model.decision_function(scaler.transform(x))
    print(json.dumps(dict(scores=scores.tolist(),runtime=dict(python=sys.version.split()[0],sklearn=sklearn.__version__)),allow_nan=False))
if __name__=='__main__':main()
