# SDNET2018 — download blocked

Official page: https://digitalcommons.usu.edu/all_datasets/48/

A scripted GET of `SDNET2018.zip` returned a Cloudflare "Just a moment..." HTML page, not the 515,903 kB archive.

**Next step:** open the official page in a browser, complete the challenge, download `SDNET2018.zip`, save it here, extract to `extracted/`, then run:

```powershell
python scripts/eda_infrascan.py --dataset sdnet2018
```
