$ErrorActionPreference = 'Continue'
$dl = @(
@('dilcrah-2017','https://static.data.gouv.fr/resources/subventions-versees-par-la-dilcrah-en-2017/20220726-172410/subventions-versees-par-la-dilcrah-en-2017.csv'),
@('dilcrah-2018','https://static.data.gouv.fr/resources/subventions-versees-par-la-dilcrah-en-2018/20220803-173802/subventions-versees-par-la-dilcrah-en-2018.csv'),
@('dilcrah-2019','https://static.data.gouv.fr/resources/subventions-versees-par-la-dilcrah-en-2019/20220804-165229/subventions-versees-par-la-dilcrah-en-2019.csv'),
@('dilcrah-2020','https://static.data.gouv.fr/resources/subventions-versees-par-la-dilcrah-en-2020/20220805-093626/subventions-versees-par-la-dilcrah-en-2020.csv'),
@('dilcrah-2021','https://static.data.gouv.fr/resources/subventions-versees-par-la-dilcrah-en-2021/20220805-114324/subventions-versees-par-la-dilcrah-en-2021.csv'),
@('dilcrah-2023','https://static.data.gouv.fr/resources/subventions-versees-par-la-diclrah-en-2023/20250115-091847/subventions-versees-par-la-dilcrah-en-2023.xlsx'),
@('charente-maritime','https://static.data.gouv.fr/resources/donnees-essentielles-des-conventions-de-subvention-1/20251218-075026/open-data-subventions.csv'),
@('cher','https://static.data.gouv.fr/resources/donnees-essentielles-des-conventions-de-subvention-8/20260114-154849/tableau-donnees-essentielles-de-subvention-sup-a-23-k-euros-decembre-2025.csv'),
@('mayenne-2018','https://static.data.gouv.fr/resources/donnees-essentielles-de-conventions-de-subvention-2018/20220118-185724/data.gouv-cd53-2018.xlsx'),
@('mayenne-2019','https://static.data.gouv.fr/resources/donnees-essentielles-de-conventions-de-subvention-2019/20220118-180900/data.gouv-cd53-2019.xlsx'),
@('mayenne-2022','https://static.data.gouv.fr/resources/donnees-essentielles-de-conventions-de-subvention-2022/20230314-155441/donnees-essentielles-de-subvention.xlsx'),
@('dordogne-2018','https://static.data.gouv.fr/resources/subventions-2018-du-departement-de-la-dordogne/20210519-104207/cd24-subventions-2018.csv'),
@('dordogne-2019','https://static.data.gouv.fr/resources/subventions-2019-du-departement-de-la-dordogne/20210519-103850/cd24-subventions-2019.csv'),
@('aube-1','https://static.data.gouv.fr/resources/conseil-departemental-de-laube-conventions-de-subvention/20171213-161239/donnees-essentielles-conventions-de-subvention.xlsx'),
@('aube-2','https://static.data.gouv.fr/resources/conseil-departemental-de-laube-conventions-de-subvention-1/20210630-150737/2021-06-donnees-essentielles-conventions-subvention.xlsx'),
@('lisieux-2018','https://static.data.gouv.fr/resources/liste-des-subventions-aux-associations-2018/20190227-102014/liste-des-subventions-aux-associations-2018.xlsx'),
@('redon-2018','https://static.data.gouv.fr/resources/ville-de-redon-subventions-aux-associations-2018/20180420-154951/subventions-2018-ville-de-redon-associations.csv'),
@('sailly-lez-lannoy','https://static.data.gouv.fr/resources/subventions-aux-associations-sailly-lez-lannoy/20221124-161901/subventions-aux-associations-feuille-1.csv'),
@('iffendic','https://static.data.gouv.fr/resources/subventions-accordees-aux-associations-par-la-commune-diffendic/20190627-162906/subv-associations-iffendic.csv'),
@('talensac','https://static.data.gouv.fr/resources/subventions-accordees-aux-associations-par-la-commune-de-talensac/20180927-120737/subv-associations-talensac.csv'),
@('efs-siege','https://static.data.gouv.fr/resources/tableau-des-subventions-accordees-par-lefs-siege/20220228-160744/tableau-etat-des-subventions-2020-2021.xlsx'),
@('efs-ocpm','https://static.data.gouv.fr/resources/tableau-des-subventions-accordees-par-lets-ocpm-1/20191011-111255/tableau-de-publication-des-donnees-essentielles-des-subventions-accordees-par-efs-ocpm-2019-.xlsx'),
@('quercy-vert-2019','https://static.data.gouv.fr/resources/conventions-de-subvention-aux-associations-exercice-2019/20200528-103703/donnees-essentielles-conventions-de-subvention-aux-associations-019.xlsx'),
@('quercy-vert-2020','https://static.data.gouv.fr/resources/conventions-de-subvention-aux-associations-exercice-2020/20210705-120923/tableau-2020-donnees-essentielles-conventions-de-subvention.xlsx'),
@('bop177','https://static.data.gouv.fr/resources/subventions-attribuees-sur-lenveloppe-du-bop-177/20190603-133744/pdl-bop-177-publication-conventions-2018.xlsx'),
@('cabinet-pm-2022','https://static.data.gouv.fr/resources/subventions-versees-par-le-cabinet-pm-en-2022/20230102-152316/subventions-versees-par-le-cabinet-pm-en-2022.csv'),
@('lannion','https://www.data.gouv.fr/storage/f/2014-04-11T11-45-08/datas-3.csv'),
@('asnieres-2025','https://static.data.gouv.fr/resources/montant-des-subventions-de-lannee-2025/20260120-145400/data-subvention.csv')
)
foreach ($pair in $dl) {
    $name = $pair[0]; $url = $pair[1]
    curl.exe -sL $url -o ("data\tmp\b16-" + $name + ".csv")
    $size = (Get-Item ("data\tmp\b16-" + $name + ".csv")).Length
    Write-Host ($name + " : " + [Math]::Round($size/1024,1) + " KB")
    Start-Sleep 1
}