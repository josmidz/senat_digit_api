from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag
from app.modules.core.enums.api_consumers import EApiConsumerFlag


DISPOSABLE_DOMAINS = [
    'tempmail.com', 'throwawaymail.com', 'mailinator.com', 'guerrillamail.com',
    'yopmail.com', '10minutemail.com', 'trashmail.com', 'mailnesia.com',
    'temp-mail.org', 'dispostable.com', 'fakeinbox.com', 'getnada.com',
    'maildrop.cc', 'tempmailaddress.com', 'throwawayemailaddress.com',
    'mytemp.email', 'tempail.com', 'mailmetrash.com', 'trashmailer.com',
    'disposablemail.com', 'tempomail.com', 'throwawaymail.cc', 'mailcatch.com',
    'inboxalias.com', 'mailmoat.com', 'mailinator.net', 'spamgourmet.com',
    'mailinator.org', 'sharklasers.com', 'guerrillamail.net',
    'guerrillamail.biz', 'guerrillamail.org', 'guerrillamail.de',
    'grr.la', 'pokemail.net', 'spam4.me', 'spam.su', 'spammotel.com',
    'spamfree24.org', 'spamfree.eu', 'spamhole.com', 'spamobox.com',
    'spamspot.com', 'tempinbox.com', 'temporaryinbox.com', 'thankyou2010.com',
    'thisisnotmyrealemail.com', 'tmail.com', 'tmailinator.com',
    'tmpmail.net', 'temporary-mail.net', 'deadaddress.com',
    'mailnull.com', 'nowmymail.com', 'sogetthis.com', 'jetable.org',
    'mail-temporaire.fr', 'harakirimail.com', 'mailhazard.com',
    'mailhazard.us', 'mailinator2.com', 'notmailinator.com',
    'dodgit.com', 'dodgit.org', 'dontsendmespam.de',
    'e4ward.com', 'emailias.com', 'fake-mail.com', 'filzmail.com',
    'getairmail.com', 'gishpuppy.com', 'gowikicdn.com', 'gowikimedia.com',
    'guerrillamail.info', 'hidzz.com', 'hmamail.com', 'hochsitze.com',
    'ieh-mail.de', 'imails.info', 'incognitomail.org', 'insorg-mail.info',
    'ipoo.org', 'irish2me.com', 'junk1e.com', 'keepmymail.com',
    'klassmaster.com', 'klzlk.com', 'kulturbetrieb.info',
    'litedrop.com', 'lol.ovpn.to', 'lookugly.com', 'lopl.co.cc',
    'lortemail.dk', 'lr78.com', 'm4ilweb.info', 'mail.bccto.me',
    'mail.by', 'mail.mezimages.net', 'mail.zp.ua', 'mail1a.de',
    'mail21.cc', 'mail2rss.org', 'mail333.com', 'mailbidon.com',
    'mailblocks.com', 'mailbucket.org', 'mailcat.biz', 'mailde.de',
    'mailde.info', 'maildx.com', 'maileater.com', 'mailexpire.com',
    'mailfa.tk', 'mailforspam.com', 'mailfreeonline.com',
    'mailfs.com', 'mailguard.me', 'mailimate.com', 'mailin8r.com',
    'mailinater.com', 'mailinator.us', 'mailincubator.com',
    'mailismagic.com', 'mailjunk.cf', 'mailmate.com', 'mailme.ir',
    'mailme24.com', 'mailmetrash.com', 'mailmoat.com', 'mailms.com',
    'mailnator.com', 'mailnesia.com', 'mailpick.biz', 'mailproxsy.com',
    'mailquack.com', 'mailrock.biz', 'mailsac.com', 'mailscrap.com',
    'mailshell.com', 'mailsiphon.com', 'mailslite.com', 'mailtemp.info',
    'mailtome.de', 'mailtothis.com', 'mailtrash.net', 'mailtv.net',
    'mailtv.tv', 'mailzi.ru', 'mailzilla.org', 'mbx.cc', 'mega.zik.dj',
    'meltmail.com', 'messagebeamer.de', 'mierdamail.com', 'mintemail.com',
    'moncourrier.fr.nf', 'monemail.fr.nf', 'monmail.fr.nf', 'mt2009.com',
    'mx0.wwwnew.eu', 'mycleaninbox.net', 'mypacks.net', 'mypartyclip.de',
    'myphantomemail.com', 'mysamp.de', 'myspaceinc.com', 'myspaceinc.net',
    'myspaceinc.org', 'myspacepimpedup.com', 'mytrashmail.com',
    'neomailbox.com', 'nepwk.com', 'nervmich.net', 'nervtmich.net',
    'netmails.com', 'netmails.net', 'netzidiot.de', 'neverbox.com',
    'nice-4u.com', 'nincsmail.hu', 'nnh.com', 'no-spam.ws', 'nobulk.com',
    'noclickemail.com', 'nogmailspam.info', 'nomail.xl.cx', 'nomail2me.com',
    'nomorespamemails.com', 'nospam.ze.tc', 'nospam4.us', 'nospamfor.us',
    'nospammail.net', 'notmailinator.com', 'nowhere.org', 'nowmymail.com',
    'nurfuerspam.de', 'objectmail.com', 'obobbo.com', 'oneoffemail.com',
    'onewaymail.com', 'online.ms', 'oopi.org', 'ordinaryamerican.net',
    'otherinbox.com', 'ourklips.com', 'outlawspam.com', 'ovpn.to',
    'owlpic.com', 'pancakemail.com', 'pcusers.otherinbox.com',
    'pepbot.com', 'pfui.ru', 'pimpedupmyspace.com', 'pjjkp.com',
    'plexolan.de', 'politikerclub.de', 'poofy.org', 'pookmail.com',
    'privacy.net', 'proxymail.eu', 'prtnx.com', 'punkass.com',
    'putthisinyourspamdatabase.com', 'quickinbox.com', 'rcpt.at',
    'recode.me', 'recursor.net', 'regbypass.com', 'regbypass.comsafe-mail.net',
    'rejectmail.com', 'rhyta.com', 'rmqkr.net', 'royal.net',
    'rtrtr.com', 's0ny.net', 'safe-mail.net', 'safersignup.de',
    'safetymail.info', 'safetypost.de', 'sandelf.de', 'saynotospams.com',
    'selfdestructingmail.com', 'sendspamhere.com', 'sharklasers.com',
    'shiftmail.com', 'shitmail.me', 'shitware.nl', 'shortmail.net',
    'sibmail.com', 'sinnlos-mail.de', 'slapsfromlastnight.com',
    'slaskpost.se', 'smashmail.de', 'smellfear.com', 'snakemail.com',
    'sneakemail.com', 'sofort-mail.de', 'sogetthis.com', 'soodonims.com',
    'spam.la', 'spam.su', 'spamavert.com', 'spambob.net', 'spambob.org',
    'spambog.com', 'spambog.de', 'spambog.ru', 'spambooger.com',
    'spambox.info', 'spambox.irishspringrealty.com', 'spambox.us',
    'spamcero.com', 'spamcon.org', 'spamcorptastic.com', 'spamcowboy.com',
    'spamcowboy.net', 'spamcowboy.org', 'spamday.com', 'spamex.com',
    'spamfree24.com', 'spamfree24.de', 'spamfree24.eu', 'spamfree24.info',
    'spamfree24.net', 'spamfree24.org', 'spamgourmet.com', 'spamherelots.com',
    'spamhereplease.com', 'spamhole.com', 'spamify.com', 'spaminator.de',
    'spamkill.info', 'spaml.com', 'spammotel.com', 'spamobox.com',
    'spamslicer.com', 'spamspot.com', 'spamthis.co.uk', 'spamthisplease.com',
    'spamtrail.com', 'speed.1s.fr', 'spoofmail.de', 'stuffmail.de',
    'supergreatmail.com', 'supermailer.jp', 'suremail.info', 'teewars.org',
    'teleworm.com', 'teleworm.us', 'temp-mail.de', 'temp-mail.ru',
    'temp.emeraldwebmail.com', 'temp.headstrong.de', 'tempalias.com',
    'tempe-mail.com', 'tempemail.biz', 'tempemail.com', 'tempemail.net',
    'tempinbox.co.uk', 'tempinbox.com', 'tempmail.co', 'tempmail.de',
    'tempmaildemo.com', 'tempmailer.com', 'tempmailer.de', 'tempomail.fr',
    'temporarily.de', 'temporarioemail.com.br', 'temporaryemail.net',
    'temporaryemail.us', 'temporaryforwarding.com', 'temporaryinbox.com',
    'thankyou2010.com', 'thisisnotmyrealemail.com', 'throwawayemail.com',
    'throwawaymail.com', 'tilien.com', 'tittbit.in', 'tmail.com',
    'tmail.ws', 'tmailinator.com', 'toiea.com', 'toomail.biz',
    'topranklist.de', 'tradermail.info', 'trash-amil.com', 'trash-mail.at',
    'trash-mail.com', 'trash-mail.de', 'trash-mail.ga', 'trash-mail.gq',
    'trash-mail.ml', 'trash-mail.tk', 'trash2009.com', 'trashemail.de',
    'trashmail.at', 'trashmail.com', 'trashmail.de', 'trashmail.me',
    'trashmail.net', 'trashmail.org', 'trashmail.ws', 'trashmailer.com',
    'trashymail.com', 'trashymail.net', 'trillianpro.com', 'turual.com',
    'twinmail.de', 'tyldd.com', 'uggsrock.com', 'upliftnow.com',
    'uplipht.com', 'venompen.com', 'veryrealemail.com', 'viditag.com',
    'viralplays.com', 'vpn.st', 'vsimcard.com', 'vubby.com',
    'wasteland.rfc822.org', 'webemail.me', 'wegwerfemail.de',
    'wegwerfmail.de', 'wegwerfmail.net', 'wegwerfmail.org',
    'wetrainbayarea.com', 'wh4f.org', 'whyspam.me', 'willselfdestruct.com',
    'winemaven.info', 'wronghead.com', 'wuzup.net', 'wuzupmail.net',
    'xagloo.com', 'xemaps.com', 'xents.com', 'xmaily.com',
    'xoxy.net', 'yep.it', 'yogamaven.com', 'yopmail.fr',
    'yopmail.net', 'youmailr.com', 'yourdomain.com', 'ypmail.webarnak.fr.eu.org',
    'yuurok.com', 'zehnminutenmail.de', 'zippymail.info', 'zoemail.net',
    'zoemail.org', 'zomg.info', '1mail.x24hr.com', '20mail.it',
    '21cn.com', '2prong.com', '30minutemail.com', '33mail.com',
    '3d-painting.com', '4warding.com', '4warding.net', '4warding.org',
    '60minutemail.com', '675hosting.com', '675hosting.net', '675hosting.org',
    '6ip.us', '6paq.com', '7tags.com', '9ox.net', 'a-bc.net',
    'afrobacon.com', 'ajaxapp.net', 'amilegit.com', 'amiri.net',
    'amiriindustries.com', 'anonbox.net', 'anonymbox.com', 'antichef.com',
    'antichef.net', 'antireg.ru', 'antispam.de', 'antispam24.de',
    'antispammail.de', 'armyspy.com', 'artman-conception.com', 'azmeil.tk',
    'baxomale.ht.cx', 'beefmilk.com', 'bigstring.com', 'binkmail.com',
    'bio-muesli.net', 'bobmail.info', 'bodhi.lawlita.com', 'bofthew.com',
    'brefmail.com', 'bsnow.net', 'bspamfree.org', 'bugmenot.com',
    'bumpymail.com', 'casualdx.com', 'centermail.com', 'centermail.net',
    'chogmail.com', 'choicemail1.com', 'cool.fr.nf', 'correo.blogos.net',
    'cosmorph.com', 'courriel.fr.nf', 'courrieltemporaire.com', 'cubiclink.com',
    'curryworld.de', 'cust.in', 'dacoolest.com', 'dandikmail.com',
    'dayrep.com', 'dcemail.com', 'deadaddress.com', 'delikkt.de',
    'despam.it', 'despammed.com', 'devnullmail.com', 'dfgh.net',
    'digitalsanctuary.com', 'dingbone.com', 'discardmail.com', 'discardmail.de',
    'disposableaddress.com', 'disposableemailaddresses.com', 'disposableinbox.com',
    'dispose.it', 'dispostable.com', 'dm.w3internet.co.uk', 'dodgeit.com',
    'dodgit.org', 'donemail.ru', 'dontreg.com', 'dontsendmespam.de',
    'dotmsg.com', 'drdrb.net', 'dump-email.info', 'dumpandjunk.com',
    'dumpmail.de', 'dumpyemail.com', 'e-mail.com', 'e-mail.org',
    'e4ward.com', 'easytrashmail.com', 'einmalmail.de', 'email60.com',
    'emaildienst.de', 'emailgo.de', 'emailias.com', 'emailigo.de',
    'emailinfive.com', 'emailmiser.com', 'emailsensei.com', 'emailtemporanea.net',
    'emailtemporario.com.br', 'emailthe.net', 'emailtmp.com', 'emailto.de',
    'emailwarden.com', 'emailx.at.hm', 'emailxfer.com', 'emeil.in',
    'emz.net', 'enterto.com', 'ephemail.net', 'ero-tube.org',
    'evopo.com', 'explodemail.com', 'express.net.ua', 'eyepaste.com',
    'fake-box.com', 'fakemailgenerator.com', 'fansworldwide.de', 'fastacura.com',
    'fastchevy.com', 'fastchrysler.com', 'fastkawasaki.com', 'fastmazda.com',
    'fastmitsubishi.com', 'fastnissan.com', 'fastsubaru.com', 'fastsuzuki.com',
    'fasttoyota.com', 'fastyamaha.com', 'fightallspam.com', 'filzmail.com',
    'fivemail.de', 'fizmail.com', 'frapmail.com', 'friendlymail.co.uk',
    'front14.org', 'fuckingduh.com', 'fudgerub.com', 'garliclife.com',
    'gehensiemirnichtaufdensack.de', 'get1mail.com', 'get2mail.fr', 'getairmail.com',
    'getmails.eu', 'getonemail.com', 'getonemail.net', 'ghosttexter.de',
    'girlsundertheinfluence.com', 'gishpuppy.com', 'gmial.com', 'goemailgo.com',
    'gotmail.net', 'gotmail.org', 'gotti.otherinbox.com', 'great-host.in',
    'greensloth.com', 'gsrv.co.uk', 'guerillamail.biz', 'guerillamail.com',
    'guerillamail.net', 'guerillamail.org', 'guerrillamailblock.com', 'gustr.com',
    'h.mintemail.com', 'h8s.org', 'haltospam.com', 'harakirimail.com',
    'hartbot.de', 'hatespam.org', 'hidemail.de', 'hidzz.com',
    'hmamail.com', 'hopemail.biz', 'hotpop.com', 'ieh-mail.de',
    'ikbenspamvrij.nl', 'imails.info', 'inboxclean.com', 'inboxclean.org',
    'inboxproxy.com', 'incognitomail.com', 'incognitomail.net', 'incognitomail.org',
    'insorg-mail.info', 'ipoo.org', 'irish2me.com', 'iwi.net',
    'jetable.com', 'jetable.fr.nf', 'jnxjn.com', 'jourrapide.com',
    'jsrsolutions.com', 'kasmail.com', 'kaspop.com', 'keepmymail.com',
    'killmail.com', 'killmail.net', 'klassmaster.com', 'klzlk.com',
    'koszmail.pl', 'kulturbetrieb.info', 'kurzepost.de', 'l33r.eu',
    'lackmail.net', 'lags.us', 'lawlita.com', 'letthemeatspam.com',
    'lhsdv.com', 'lifebyfood.com', 'link2mail.net', 'litedrop.com',
    'lol.ovpn.to', 'lookugly.com', 'lopl.co.cc', 'lortemail.dk',
    'lr78.com', 'lroid.com', 'luv2.us', 'm4ilweb.info',
    'maboard.com', 'mail-filter.com', 'mail-temporaire.fr', 'mail.by',
    'mail.mezimages.net', 'mail.zp.ua', 'mail1a.de', 'mail21.cc',
    'mail2rss.org', 'mail333.com', 'mail4trash.com', 'mailbidon.com',
    'mailbiz.biz', 'mailblocks.com', 'mailbucket.org', 'mailcat.biz',
    'mailcatch.com', 'mailde.de', 'mailde.info', 'maildrop.cc',
    'maildx.com', 'maileater.com', 'mailexpire.com', 'mailfa.tk',
    'mailforspam.com', 'mailfreeonline.com', 'mailfs.com', 'mailguard.me',
    'mailimate.com', 'mailin8r.com', 'mailinater.com', 'mailinator.com',
    'mailinator.net', 'mailinator.org', 'mailinator.us', 'mailinator2.com',
    'mailincubator.com', 'mailismagic.com', 'mailjunk.cf', 'mailmate.com',
    'mailme.ir', 'mailme24.com', 'mailmetrash.com', 'mailmoat.com',
    'mailms.com', 'mailnator.com', 'mailnesia.com', 'mailnull.com',
    'mailpick.biz', 'mailproxsy.com', 'mailquack.com', 'mailrock.biz',
    'mailsac.com', 'mailscrap.com', 'mailshell.com', 'mailsiphon.com',
    'mailslite.com', 'mailtemp.info', 'mailtome.de', 'mailtothis.com',
    'mailtrash.net', 'mailtv.net', 'mailtv.tv', 'mailzi.ru',
    'mailzilla.org', 'mailzilla.orgmbx.cc', 'makemetheking.com', 'manybrain.com',
    'mbx.cc', 'mega.zik.dj', 'meltmail.com', 'messagebeamer.de',
    'mierdamail.com', 'mintemail.com', 'moburl.com', 'moncourrier.fr.nf',
    'monemail.fr.nf', 'monmail.fr.nf', 'msa.minsmail.com', 'mt2009.com',
    'mx0.wwwnew.eu', 'mycleaninbox.net', 'mypacks.net', 'mypartyclip.de',
    'myphantomemail.com', 'mysamp.de', 'myspaceinc.com', 'myspaceinc.net',
    'myspaceinc.org', 'myspacepimpedup.com', 'mytrashmail.com', 'neomailbox.com',
    'nepwk.com', 'nervmich.net', 'nervtmich.net', 'netmails.com',
    'netmails.net', 'netzidiot.de', 'neverbox.com', 'nice-4u.com',
    'nincsmail.hu', 'nnh.com', 'no-spam.ws', 'nobulk.com',
    'noclickemail.com', 'nogmailspam.info', 'nomail.xl.cx', 'nomail2me.com',
    'nomorespamemails.com', 'nospam.ze.tc', 'nospam4.us', 'nospamfor.us',
    'nospammail.net', 'notmailinator.com', 'nowhere.org', 'nowmymail.com',
    'nurfuerspam.de', 'objectmail.com', 'obobbo.com', 'oneoffemail.com',
    'onewaymail.com', 'online.ms', 'oopi.org', 'ordinaryamerican.net',
    'otherinbox.com', 'ourklips.com', 'outlawspam.com', 'ovpn.to',
    'owlpic.com', 'pancakemail.com', 'pcusers.otherinbox.com', 'pepbot.com',
    'pfui.ru', 'pimpedupmyspace.com', 'pjjkp.com', 'plexolan.de',
    'politikerclub.de', 'poofy.org', 'pookmail.com', 'privacy.net',
    'proxymail.eu', 'prtnx.com', 'punkass.com', 'putthisinyourspamdatabase.com',
    'quickinbox.com', 'rcpt.at', 'recode.me', 'recursor.net',
    'regbypass.com', 'regbypass.comsafe-mail.net', 'rejectmail.com', 'rhyta.com',
    'rmqkr.net', 'royal.net', 'rtrtr.com', 's0ny.net',
    'safe-mail.net', 'safersignup.de', 'safetymail.info', 'safetypost.de',
    'sandelf.de', 'saynotospams.com', 'selfdestructingmail.com', 'sendspamhere.com',
    'sharklasers.com', 'shiftmail.com', 'shitmail.me', 'shitware.nl',
    'shortmail.net', 'sibmail.com', 'sinnlos-mail.de', 'slapsfromlastnight.com',
    'slaskpost.se', 'smashmail.de', 'smellfear.com', 'snakemail.com',
    'sneakemail.com', 'sofort-mail.de', 'sogetthis.com', 'soodonims.com',
    'spam.la', 'spam.su', 'spamavert.com', 'spambob.net',
    'spambob.org', 'spambog.com', 'spambog.de', 'spambog.ru',
    'spambooger.com', 'spambox.info', 'spambox.irishspringrealty.com', 'spambox.us',
    'spamcero.com', 'spamcon.org', 'spamcorptastic.com', 'spamcowboy.com',
    'spamcowboy.net', 'spamcowboy.org', 'spamday.com', 'spamex.com',
    'spamfree24.com', 'spamfree24.de', 'spamfree24.eu', 'spamfree24.info',
    'spamfree24.net', 'spamfree24.org', 'spamgourmet.com', 'spamherelots.com',
    'spamhereplease.com', 'spamhole.com', 'spamify.com', 'spaminator.de',
    'spamkill.info', 'spaml.com', 'spammotel.com', 'spamobox.com',
    'spamslicer.com', 'spamspot.com', 'spamthis.co.uk', 'spamthisplease.com',
    'spamtrail.com', 'speed.1s.fr', 'spoofmail.de', 'stuffmail.de',
    'supergreatmail.com', 'supermailer.jp', 'suremail.info', 'teewars.org',
    'teleworm.com', 'teleworm.us', 'temp-mail.de', 'temp-mail.ru',
    'temp.emeraldwebmail.com', 'temp.headstrong.de', 'tempalias.com',
    'tempe-mail.com', 'tempemail.biz', 'tempemail.com', 'tempemail.net',
    'tempinbox.co.uk', 'tempinbox.com', 'tempmail.co', 'tempmail.de',
    'tempmaildemo.com', 'tempmailer.com', 'tempmailer.de', 'tempomail.fr',
    'temporarily.de', 'temporarioemail.com.br', 'temporaryemail.net',
    'temporaryemail.us', 'temporaryforwarding.com', 'temporaryinbox.com',
    'thankyou2010.com', 'thisisnotmyrealemail.com', 'throwawayemail.com',
    'throwawaymail.com', 'tilien.com', 'tittbit.in', 'tmail.com',
    'tmail.ws', 'tmailinator.com', 'toiea.com', 'toomail.biz',
    'topranklist.de', 'tradermail.info', 'trash-amil.com', 'trash-mail.at',
    'trash-mail.com', 'trash-mail.de', 'trash-mail.ga', 'trash-mail.gq',
    'trash-mail.ml', 'trash-mail.tk', 'trash2009.com', 'trashemail.de',
    'trashmail.at', 'trashmail.com', 'trashmail.de', 'trashmail.me',
    'trashmail.net', 'trashmail.org', 'trashmail.ws', 'trashmailer.com',
    'trashymail.com', 'trashymail.net', 'trillianpro.com', 'turual.com',
    'twinmail.de', 'tyldd.com', 'uggsrock.com', 'upliftnow.com',
    'uplipht.com', 'venompen.com', 'veryrealemail.com', 'viditag.com',
    'viralplays.com', 'vpn.st', 'vsimcard.com', 'vubby.com',
    'wasteland.rfc822.org', 'webemail.me', 'wegwerfemail.de',
    'wegwerfmail.de', 'wegwerfmail.net', 'wegwerfmail.org',
    'wetrainbayarea.com', 'wh4f.org', 'whyspam.me', 'willselfdestruct.com',
    'winemaven.info', 'wronghead.com', 'wuzup.net', 'wuzupmail.net',
    'xagloo.com', 'xemaps.com', 'xents.com', 'xmaily.com',
    'xoxy.net', 'yep.it', 'yogamaven.com', 'yopmail.fr',
    'yopmail.net', 'youmailr.com', 'yourdomain.com', 'ypmail.webarnak.fr.eu.org',
    'yuurok.com', 'zehnminutenmail.de', 'zippymail.info', 'zoemail.net',
    'zoemail.org', 'zomg.info'
]


REGION_TO_COUNTRY_CODE = {
    # North America
    'US': '1', 'CA': '1', 'PR': '1', 'DO': '1', 'JM': '1',
    'TT': '1', 'BS': '1', 'BB': '1', 'AG': '1', 'VC': '1',
    'GD': '1', 'KN': '1', 'LC': '1', 'DM': '1', 'VG': '1',

    # Europe
    'GB': '44', 'FR': '33', 'DE': '49', 'IT': '39', 'ES': '34',
    'NL': '31', 'BE': '32', 'CH': '41', 'AT': '43', 'SE': '46',
    'NO': '47', 'FI': '358', 'DK': '45', 'PL': '48', 'CZ': '420',
    'HU': '36', 'RO': '40', 'IE': '353', 'GR': '30', 'PT': '351',
    'RU': '7', 'UA': '380', 'BY': '375', 'KZ': '7', 'TR': '90',
    'IL': '972', 'SA': '966', 'AE': '971', 'QA': '974', 'KW': '965',

    # Asia
    'CN': '86', 'JP': '81', 'KR': '82', 'IN': '91', 'ID': '62',
    'PK': '92', 'BD': '880', 'TH': '66', 'PH': '63', 'VN': '84',
    'MY': '60', 'SG': '65', 'LK': '94', 'NP': '977', 'MM': '95',
    'KH': '855', 'LA': '856', 'TW': '886', 'HK': '852', 'MO': '853',

    # Africa
    'NG': '234', 'EG': '20', 'ZA': '27', 'KE': '254', 'ET': '251',
    'GH': '233', 'DZ': '213', 'MA': '212', 'TN': '216', 'LY': '218',
    'SD': '249', 'CD': '243', 'TZ': '255', 'UG': '256', 'ZM': '260',
    'ZW': '263', 'MW': '265', 'MZ': '258', 'AO': '244', 'CM': '237',

    # South America
    'BR': '55', 'MX': '52', 'AR': '54', 'CO': '57', 'PE': '51',
    'VE': '58', 'CL': '56', 'EC': '593', 'BO': '591', 'PY': '595',
    'UY': '598', 'CR': '506', 'PA': '507', 'GT': '502', 'SV': '503',
    'HN': '504', 'NI': '505',

    # Oceania
    'AU': '61', 'NZ': '64', 'FJ': '679', 'PG': '675', 'SB': '677',

    # Caribbean
    'CU': '53', 'HT': '509', 'SR': '597', 'GY': '592', 'BZ': '501',

    # Middle East
    'IR': '98', 'IQ': '964', 'SY': '963', 'LB': '961', 'JO': '962',
    'PS': '970', 'YE': '967', 'OM': '968', 'BH': '973',

    # Others
    'IS': '354', 'GL': '299', 'FO': '298', 'AX': '358', 'SJ': '47',
    'MV': '960', 'BT': '975', 'MN': '976', 'TL': '670', 'BN': '673',
    'FM': '691', 'PW': '680', 'TO': '676', 'WS': '685', 'VU': '678',
    'KI': '686', 'TV': '688'
}

# List of common free email providers and disposable domains
FREE_EMAIL_DOMAINS = [
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'mail.com', 'protonmail.com', 'zoho.com', 'yandex.com',
    'gmx.com', 'live.com', 'msn.com', 'me.com', 'inbox.com',
    'fastmail.com', 'tutanota.com', 'mail.ru', 'qq.com', '163.com',
    '126.com', 'sina.com', 'naver.com', 'daum.net', 'hanmail.net',
    'rocketmail.com', 'att.net', 'verizon.net', 'comcast.net', 'charter.net',
    'rediffmail.com', 'libero.it', 'wp.pl', 'onet.pl', 'o2.pl'
]

# Cascade children configuration mapping
# This defines parent-child relationships between collections for cascade operations
CASCADE_CHILDREN_MAPPING = {
    CollectionKey.ARCH_FOLDER.value: [
        {
            "collection_name": CollectionKey.ARCH_FILE.value,
            "field_name": "arch_folder_id"
        }
    ],
    CollectionKey.SYS_ORGANIZATION.value: [
        {
            "collection_name": CollectionKey.SYS_USER.value,
            "field_name": "sys_organization_id"
        },
        {
            "collection_name": CollectionKey.RBAC_PROFILE.value,
            "field_name": "sys_organization_id"
        }
    ],
    CollectionKey.SYS_MENU.value: [
        {
            "collection_name": CollectionKey.SYS_MENU.value,
            "field_name": "parent_menu_id"
        }
    ],

}

ALL_PROFIL_IN_ONE = [
    {
        "flag": ESysProfileFlag.MAIN_PROFILE.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfileFlag.SYSTEM_PROFIL.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]


TEST_PROFIL_IN_ONE = [
    {
        "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]
MAIN_PROFILE_IN_ONE = [
    {
        "flag": ESysProfileFlag.MAIN_PROFILE.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]
TRANS_CLIENT_ANGENT_PROFIL_IN_ONE = [
    {
        "flag": ESysProfileFlag.TRANS_VISITOR.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfileFlag.TRANS_CUSTOMER.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfileFlag.MAIN_PROFILE.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]


SYSTEM_ORGANIZATION_PROFIL_IN_ONE = [
    {
        "flag": ESysProfileFlag.SYSTEM_PROFIL.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]

ALL_ORGANIZATION_PROFIL_IN_ONE = [
    {
        "flag": ESysProfileFlag.MAIN_PROFILE.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfileFlag.SYSTEM_PROFIL.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]

ALL_OTHERS_ORGANIZATION_PROFIL_IN_ONE = [

    {
        "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]

# ────────────────────────────────────────────────────────────────────────
# User-app-store cache whitelists.
#
# STATIC profiles share a single cache row across every user with that
# profile (visitor, customer-class — same menu set for everyone). DYNAMIC
# profiles get one cache row per user (admin/agent — RBAC tree differs
# per tenant + per role assignment).
#
# When a profile flag isn't in either list, the cache layer treats it as
# DYNAMIC by default (one row per user). Add to STATIC only when you're
# certain every user with that profile sees the exact same app list.
# ────────────────────────────────────────────────────────────────────────

USER_APP_STORE_STATIC_PROFILES = [
    ESysProfileFlag.TRANS_VISITOR.value,
    ESysProfileFlag.TRANS_CUSTOMER.value,
]

USER_APP_STORE_AVAILABLE_DYNAMIC_PROFILES = [
    ESysProfileFlag.SYSTEM_PROFIL.value,
    ESysProfileFlag.MAIN_PROFILE.value,
]

USER_APP_STORE_AVAILABLE_DYNAMIC_API_CONSUMERS = [
    EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
    EApiConsumerFlag.SENAT_DIGIT_MOBILE.value,
    # FS is server-to-server and never serves a /get-applications response,
    # so it doesn't get a cache row.
]

SYSTEM_SUPER_ADMIN_ROLE_IN_ONE = [
    {
        "flag": ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]

TEST_ADMIN_ROLE_IN_ONE = [
    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]

TRANS_ADMIN_ROLE_IN_ONE = [
    {
        "flag": ESysProfilSuperUserRoleFlag.MAIN_PROFILE_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]
TRANS_FINANCER_ROLE_IN_ONE = [
    {
        "flag": ESysProfilSuperUserRoleFlag.TRANS_FINANCER_ROLE,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]
TRANS_EXPENSE_TYPE_PERSON_ROLE_IN_ONE = [
    {
        "flag": ESysProfilSuperUserRoleFlag.TRANS_EXPENSE_TYPE_PERSON_ROLE,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]

TRANS_RH_ROLE_IN_ONE = [
    {
        "flag": ESysProfilSuperUserRoleFlag.TRANS_RH_ROLE,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]
TRANS_ACCOUNTANT_ROLE_IN_ONE = [
    {
        "flag": ESysProfilSuperUserRoleFlag.TRANS_ACCOUTANT_ROLE,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]


ALL_ORGANIZATION_SUPER_ADMIN_ROLE_IN_ONE = [
    {
        "flag": ESysProfilSuperUserRoleFlag.MAIN_PROFILE_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]

ALL_OTHERS_ORGANIZATION_SUPER_ADMIN_ROLE_IN_ONE = [

    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]


FLUTTER_AGENT_APP_API_CONSUMER_IN_ONE = [
    {
        "flag": EApiConsumerFlag.SENAT_DIGIT_MOBILE.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },

]

ANGULAR_API_CONSUMER_IN_ONE = [
    {
        "flag": EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },

]

ALL_API_CONSUMER_IN_ONE = [
    {
        "flag": EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": EApiConsumerFlag.SENAT_DIGIT_MOBILE.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": EApiConsumerFlag.CLIENT_POSTMAN.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": EApiConsumerFlag.FLUTTER_VALIDATION_AND_TOTP_MFA_APPS.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },

]

SENAT_DIGIT_ADMIN_WEB_IN_ONE = [
    {
        "flag": EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]

ALL_ORGANIZATION_ADMIN_ROLE_IN_ONE = [

    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.MAIN_PROFILE_SUPER_ADMIN.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
]

ALL_STATIC_ROLE_IN_ONE = [

    {
        "flag": ESysProfilSuperUserRoleFlag.MAIN_PROFILE_SUPER_ADMIN.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },
    {
        "flag": ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN.value,
        "is_link_activated": True,
        "is_link_hidden": False,
        "is_link_locked": False,
        "is_link_deleted": False,
    },



]
