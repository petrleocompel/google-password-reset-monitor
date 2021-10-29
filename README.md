# Google password monitor
It just tryies to log in Gmail by IMAP and thats it.
## Why?
> My grandfather has a wierd "hobby". Buying a Android phone, logging in his Google account...
> Sadly my grandfather does not remember his password. NEVER!!! Soo we were out of rememable passwords really soon. And Google does not allow forbid password change.
> Sad story continues. This man cannot be stopped by 2FA, SMS codes etc... And because Android phones these days have "high" security protection aginst factory resets (**Google FRP**) we have multiple Android devices with unknown Google accounts. 
> This is a example where **FRP** is bad. *(Nothing aginst that feature just making my life hard because I reseted and bypased almost 40 mobile phones at this point...)*
> **So there We have it Google password reset monitor script** + combined with watching "accounts.google.com" on DNS resolver in special subnet for wifi devices - Almost perfect

## Whats next?
Nothing. I do not care. I am not going to publish this docker image. I am not going to invest more time in this anymore.
It just tryies to log in Gmail by IMAP and thats it.

## Configuration
Use `.env.example` to create `.env`.

Modify:
- email
- password
- webhook (Discord compatible)

## FAQ - other problems
### Not working?
Sadly - your problem

### Google IMAP enable
*AKA less secure apps* in eyes of Google
[https://support.google.com/accounts/answer/6010255](https://support.google.com/accounts/answer/6010255)

### Google Workspace for somebody
[https://support.google.com/a/answer/105694](https://support.google.com/a/answer/105694)
