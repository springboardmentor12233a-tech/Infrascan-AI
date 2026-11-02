"""InfraScan Milestone 2 machine-learning package.

The modules here are imported by the FastAPI app and by the training scripts.
PyTorch is imported only when a model is actually loaded, so the API can still
start on a machine that does not have PyTorch installed.
"""
