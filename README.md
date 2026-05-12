# qfin_tut
# Qiskit Finance Environment Setup

This guide helps you set up a dedicated Conda environment for working with the Qiskit Finance tutorials and development environment.

---

## Prerequisites

Make sure the following are installed on your system:

- Anaconda or Miniconda
- Python 3.12 support

---

# Step 1: Create Conda Environment

Create a new Conda environment named `qfin` with Python 3.12.

```bash
conda create --name qfin python=3.12
conda activate qfin
git clone https://github.com/qiskit-community/qiskit-finance.git
cd qfin_tut/
pip install -r requirements-dev.txt
pip install qiskit-algorithms qiskit-optimization qiskit-finance qiskit-aer
pip install jupyterlab
jupyter lab
qfin_tut/
│
└── tutorials/
├── requirements-dev.txt
└── README.md
