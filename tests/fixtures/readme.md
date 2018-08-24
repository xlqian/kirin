# Test fixtures

## Content

This directory groups test fixtures for IRE and COTS processing.

### COTS file cots_train _96231_delayed.json

File `cots_train _96231_delayed.json` is a bit specific:
* It's a complete train (so is corresponding IRE)
* This fixture is supposed to behave like corresponding IRE `train _96231_delayed.xml` (if we use the right fields) :
    * First delayed stop has multiple different values on purpose.  
      Those values are not consistent but will help us detect if we use a wrong field.
    * Other stops are consistent
