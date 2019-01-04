# -*- coding: utf-8 -*-
"""
Created on Thu Jan  3 17:04:49 2019

@author: piccini
"""

import requests

endpoint = 'https://mc-api-activation-reactor-integration.adobe.io'
imsUserID = 'B6400C515B6978B40A495E75@AdobeID'
clientId= "Activation-DTM"
## to be retrieved from Console
imsAccessToken = 'eyJ4NXUiOiJpbXNfbmExLWtleS0xLmNlciIsImFsZyI6IlJTMjU2In0.eyJpZCI6IjE1NDY2MDk0Njc4ODFfYTVmOGVhM2EtMWJmNC00OTM2LWI2ZDctNmVjNzAzY2E4MmE3X3VlMSIsImNsaWVudF9pZCI6IkFjdGl2YXRpb24tRFRNIiwidXNlcl9pZCI6IkI2NDAwQzUxNUI2OTc4QjQwQTQ5NUU3NUBBZG9iZUlEIiwic3RhdGUiOiJ7XCJzZXNzaW9uXCI6XCJodHRwczovL2ltcy1uYTEuYWRvYmVsb2dpbi5jb20vaW1zL3Nlc3Npb24vdjEvTmpWbFpqSXpPVGN0TVRVME1TMDBNamxqTFdFMk4yVXRORGt6TkRneVpHTTRaR0ZoTFMxQ05qUXdNRU0xTVRWQ05qazNPRUkwTUVFME9UVkZOelZBUVdSdlltVkpSQVwifSIsInR5cGUiOiJhY2Nlc3NfdG9rZW4iLCJhcyI6Imltcy1uYTEiLCJmZyI6IlRDSVpRTE40WExQMzdQUFgyNE5RQUFBQUtBPT09PT09Iiwic2lkIjoiMTU0NjYwNDM3MDk5N18zMzhkMThhNi1hOTllLTQ2NDQtYWE4Zi1jYzlkM2ZjYzc5MWNfdWUxIiwibW9pIjoiZDBhMDk1YTIiLCJjIjoiUGgzVGpaNWR0eURVMmYxcmRUcWN1UT09IiwiZXhwaXJlc19pbiI6Ijg2NDAwMDAwIiwiY3JlYXRlZF9hdCI6IjE1NDY2MDk0Njc4ODEiLCJzY29wZSI6Im9wZW5pZCxBZG9iZUlELHNlc3Npb24scmVhZF9vcmdhbml6YXRpb25zLGFkZGl0aW9uYWxfaW5mby5wcm9qZWN0ZWRQcm9kdWN0Q29udGV4dCxhZGRpdGlvbmFsX2luZm8uam9iX2Z1bmN0aW9uLGFkZGl0aW9uYWxfaW5mby5yb2xlcyJ9.iFo6EBoEh6I4cnACgloTnCTnj1-K3ly9vsr4qAnxQFGPT1QhjW3dm2dcgsO747ZfVk8gx50r0SaKIIiYidcLYaPqrIJ7Ess6N1kvVMlYsQ_NTOSVVaWUJ6DBYrxQEr8mkGa6pehiXEwN-gI5mEo8xwyCRclus2dbJZkfro5W3JPeCmZC2tF2zqlIioORI0-7kBwXQ7BtuCXZFbseZkgpZ2nOFuLHkX6rc2WgylG-WFdWeAH3cy-dH1fwXAlwgMaGM8EIS7IqYP0K1--SpMughZ20GG2Lzxr7Q3Jx0OChpLdc7Lr0uiZFWCyJurEFJehfoLvkZTBdzbRRtKvjKcprDA' 

header = {"Accept": "application/vnd.api+json;revision=1",
           "Content-Type": "application/vnd.api+json",
           "Authorization": "Bearer "+imsAccessToken,
           "X-Api-Key": clientId
           }

getCompanies = '/companies'

response = requests.get(endpoint+getCompanies,headers=header)