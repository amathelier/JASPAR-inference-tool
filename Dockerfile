FROM docker.io/continuumio/miniconda3:24.1.2-0

LABEL org.opencontainers.image.title="JASPAR Profile Inference Tool"
LABEL org.opencontainers.image.version="2026"

WORKDIR /opt/jaspar-inference

# Install conda environment (cached until environment.runtime.yml changes)
COPY conda/environment.runtime.yml ./conda/environment.runtime.yml
RUN conda env create -f conda/environment.runtime.yml && \
    conda clean -afy

ENV PATH=/opt/conda/envs/JASPAR-profile-inference/bin:$PATH

# Copy source
COPY __init__.py infer_profile.py infer_homolog.py make_html.py ./

# Copy pre-built data (largest layer — placed last so source edits don't
# invalidate it)
COPY files/ ./files/

# Named wrappers on PATH so Apptainer exec (which bypasses ENTRYPOINT) can
# call them by name. Using absolute python path avoids PATH inheritance issues.
RUN printf '#!/bin/sh\nexec /opt/conda/envs/JASPAR-profile-inference/bin/python /opt/jaspar-inference/infer_profile.py "$@"\n' \
        > /usr/local/bin/infer_profile && \
    printf '#!/bin/sh\nexec /opt/conda/envs/JASPAR-profile-inference/bin/python /opt/jaspar-inference/infer_homolog.py "$@"\n' \
        > /usr/local/bin/infer_homolog && \
    printf '#!/bin/sh\nexec /opt/conda/envs/JASPAR-profile-inference/bin/python /opt/jaspar-inference/make_html.py "$@"\n' \
        > /usr/local/bin/make_html && \
    chmod +x /usr/local/bin/infer_profile /usr/local/bin/infer_homolog \
             /usr/local/bin/make_html

ENTRYPOINT ["python", "/opt/jaspar-inference/infer_profile.py"]
