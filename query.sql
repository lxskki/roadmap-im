SELECT
    [System.Id],
    [System.WorkItemType],
    [System.Title],
    [System.AssignedTo],
    [System.State],
    [System.AreaPath],
    [System.CreatedDate],
    [Microsoft.VSTS.Scheduling.StartDate],
    [Microsoft.VSTS.Scheduling.TargetDate],
    [System.Parent],
    [Microsoft.VSTS.Scheduling.Effort],
    [Microsoft.VSTS.Common.BusinessValue],
    [System.Tags],
    [Custom.data_incl],
    [Microsoft.VSTS.Common.ClosedDate]
FROM workitems
WHERE
    [System.TeamProject] = 'inteligencia_de_mercado'
    AND (
        [System.ChangedDate] > @today - 365
        AND (
            [System.WorkItemType] = 'Feature'
            OR [System.WorkItemType] = 'Projeto'
            OR [System.WorkItemType] = 'Epic'
            OR [System.WorkItemType] = 'User Story'
        )
        AND [System.State] <> ''
    )