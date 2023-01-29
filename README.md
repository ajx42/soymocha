# soymocha

- Conda needs to be pre-installed, our scripts don't install it.
- Use _small-lan_ profile in cloudlab, scripts don't check the profile for you.

# General work flow
1. Copy over cloudlab manifest to an xml file.
2. Use setuptool to prepare scripts and launch

# Example ethereum setup

```shell
python scripts/setuptool.py --app ethereum --manifest manifest.xml --pvt-key ~/.ssh/id_ed25519 --session saladbowl
```