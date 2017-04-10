export default {
    'width': 800,
    'height': 500,
    'padding': 'strict',
    'data': [
        {
            'name': 'table',
            'values': [
            ],
            'transform': [
                {
                    'type': 'formula',
                    'field': 'adjElapsed',
                    'expr': 'clamp(datum["elapsed"]/1000,-86400,86400)'
                }
            ]
        },
        {
            'name': 'positive',
            'source': 'table',
            'transform': [
                {
                    'type': 'filter',
                    'test': 'datum.adjElapsed > 0'
                }
            ]
        },
        {
            'name': 'negative',
            'source': 'table',
            'transform': [
                {
                    'type': 'filter',
                    'test': 'datum.adjElapsed < 0'
                }
            ]
        },
        {
            'name': 'stats',
            'source': 'table',
            'transform': [
                {
                    'type': 'aggregate',
                    'groupby': ['id', 'title', 'currentStatus'],
                    'summarize': [
                        {
                            'field': 'adjElapsed',
                            'ops': ['sum'],
                            'as': ['sum_y']
                        }
                    ]
                }
            ]
        },
        {
            'name': 'status',
            'source': 'negative',
            'transform': [
                {
                    'type': 'aggregate',
                    'summarize': [
                        {
                            'field': 'adjElapsed',
                            'ops': ['min'],
                            'as': ['min_y']
                        }
                    ]
                },
                {
                    'type': 'cross',
                    'with': 'stats'
                }
            ]
        }
    ],
    'scales': [
        {
            'name': 'x',
            'type': 'ordinal',
            'range': 'width',
            'domain': { 'data': 'table', 'field': 'id' }
        },
        {
            'name': 'y',
            'type': 'linear',
            'range': 'height',
            'clamp': true,
            'domain': {
                'fields': [
                    { 'data': 'table', 'field': 'adjElapsed' },
                    { 'data': 'stats', 'field': 'sum_y' }
                ]
            }
        },
        {
            'name': 'color',
            'type': 'ordinal',
            'range': 'category20c',
            'domain': [{ 'data': 'table', 'field': 'status' }]
        },
        {
            'name': 'xlabels',
            'type': 'ordinal',
            'domain': [],
            'range': []
        }
    ],
    'axes': [
        {
            'type': 'x',
            'scale': 'x',
            'orient': 'bottom',
            'ticks': 0,
            'subdivide': 4,
            'properties': {
                'labels': {
                    'text': { 'scale': 'xlabels' },
                    'angle': { 'value': 50 },
                    'align': { 'value': 'left' },
                    'itemName': { 'value': 'xlabel' },
                    'dy': { 'value': 5 },
                    'dx': { 'value': 7 }
                }
            }
        },
        {
            'type': 'y',
            'scale': 'y',
            'format': 's',
            'title': 'seconds',
            'properties': {
                'labels': {
                    'itemName': { 'value': 'ylabel' }
                }
            }
        }
    ],
    'signals': [
        {
            'name': 'hover',
            'init': { 'pos': {}, 'datum': {} },
            'streams': [
                {
                    'type': 'rect:mousemove',
                    'expr': '{ pos: {x: eventX(), y: eventY()}, datum:datum}'
                },
                {
                    'type': 'rect:mouseout',
                    'expr': '{pos:{},datum:{}}'
                }
            ]
        },
        {
            'name': 'tt0',
            'init': {},
            'expr': '{ title:hover.datum.title, updated:hover.datum.updated, status:!hover.datum.status?"":hover.datum.status+":", elapsed:abs(hover.datum["elapsed"]) }'
        },
        {
            'name': 'tt1',
            'init': {},
            'expr': '{ elapsed:!tt0.elapsed?"":timeFormat(tt0.elapsed>3600000? "%H:%M:%S.%Ls":(tt0.elapsed>60000?"%M:%S.%Ls":"%S.%Ls"), datetime(0,0,0,0,0,0,tt0.elapsed)) }'
        },
        {
            'name': 'tt2',
            'init': {},
            'expr': '{ width:!tt0.title?0:max(max(max(tt0.title.length,tt0.status.length),tt1.elapsed.length),tt0.updated.length)*7 }'
        },
        {
            'name': 'tooltip',
            'init': {},
            'expr': '{ y:hover.pos.y+30, x:(hover.pos.x>width-tt2.width+5?hover.pos.x-tt2.width-5:hover.pos.x+5), width:tt2.width, title:tt0.title, updated:tt0.updated, status:tt0.status, elapsed:tt1.elapsed }'
        },
        {
            'name': 'sHover',
            'init': { 'pos': {}, 'datum': {} },
            'streams': [
                {
                    'type': '@status:mousemove',
                    'expr': '{ pos: {x: eventX(), y: eventY()}, datum:datum}'
                },
                {
                    'type': '@status:mouseout',
                    'expr': '{pos:{},datum:{}}'
                }
            ]
        },
        {
            'name': 'stt0',
            'init': {},
            'expr': '{ status:sHover.datum.b?sHover.datum.b.currentStatus:"" }'
        },
        {
            'name': 'stt1',
            'init': {},
            'expr': '{ width:(stt0.status?stt0.status.length:0)*9 }'
        },
        {
            'name': 'sTooltip',
            'init': {},
            'expr': '{ y:sHover.pos.y+30, x:(sHover.pos.x>width-stt1.width+5?sHover.pos.x-stt1.width-5:sHover.pos.x+5), width:stt1.width, status:stt0.status }'
        }
    ],
    'marks': [
        {
            'type': 'rect',
            'name': 'timing',
            'from': {
                'data': 'positive',
                'transform': [
                    {
                        'type': 'stack',
                        'groupby': ['id'],
                        'field': 'adjElapsed'
                    }
                ]
            },
            'properties': {
                'enter': {
                    'x': { 'scale': 'x', 'field': 'id' },
                    'width': { 'scale': 'x', 'band': true, 'offset': -2 },
                    'y': { 'scale': 'y', 'field': 'layout_start' },
                    'y2': { 'scale': 'y', 'field': 'layout_end' },
                    'fill': { 'scale': 'color', 'field': 'status' },
                    'itemName': { 'value': 'bar' },
                    'cursor': { 'value': 'pointer' }
                },
                'update': { 'fillOpacity': { 'value': 1 } },
                'hover': {
                    'fillOpacity': { 'value': 0.5 }
                }
            }
        },
        {
            'type': 'rect',
            'name': 'timing',
            'from': {
                'data': 'negative',
                'transform': [
                    {
                        'type': 'stack',
                        'groupby': ['id'],
                        'field': 'adjElapsed'
                    }
                ]
            },
            'properties': {
                'enter': {
                    'x': { 'scale': 'x', 'field': 'id' },
                    'width': { 'scale': 'x', 'band': true, 'offset': -2 },
                    'y': { 'scale': 'y', 'field': 'layout_start' },
                    'y2': { 'scale': 'y', 'field': 'layout_end' },
                    'fill': { 'scale': 'color', 'field': 'status' },
                    'itemName': { 'value': 'bar' }
                },
                'update': { 'fillOpacity': { 'value': 1 } },
                'hover': {
                    'fillOpacity': { 'value': 0.5 }
                }
            }
        },
        {
            'name': 'status',
            'type': 'rect',
            'from': {
                'data': 'status'
            },
            'properties': {
                'enter': {
                    'width': { 'scale': 'x', 'band': true, 'offset': -4 },
                    'height': { 'value': 6 },
                    'x': { 'scale': 'x', 'field': 'b.id', 'offset': 1 },
                    'y': { 'scale': 'y', 'field': 'a.min_y', 'offset': 9 },
                    'fill': { 'scale': 'color', 'field': 'b.currentStatus' },
                    'itemName': { 'value': 'status' }
                },
                'update': { 'fillOpacity': { 'value': 1 } },
                'hover': {
                    'fillOpacity': { 'value': 0.5 }
                }
            }
        },
        {
            'name': 'timingTooltip',
            'type': 'group',
            'properties': {
                'update': {
                    'x': { 'signal': 'tooltip.x' },
                    'y': { 'signal': 'tooltip.y' },
                    'width': { 'signal': 'tooltip.width' },
                    'height': { 'value': 65 },
                    'fill': { 'value': '#fff' },
                    'fillOpacity': { 'value': 1 },
                    'stroke': { 'value': '#aaa' },
                    'strokeWidth': { 'value': 0.5 }
                }
            },
            'marks': [
                {
                    'name': 'title',
                    'type': 'text',
                    'properties': {
                        'update': {
                            'x': { 'value': 6 },
                            'y': { 'value': 14 },
                            'text': { 'signal': 'tooltip.title' },
                            'fill': { 'value': 'black' }
                        }
                    }
                },
                {
                    'name': 'title',
                    'type': 'text',
                    'properties': {
                        'update': {
                            'x': { 'value': 6 },
                            'y': { 'value': 29 },
                            'text': { 'signal': 'tooltip.updated' },
                            'fill': { 'value': 'black' }
                        }
                    }
                },
                {
                    'name': 'status',
                    'type': 'text',
                    'properties': {
                        'update': {
                            'x': { 'value': 6 },
                            'y': { 'value': 44 },
                            'text': { 'signal': 'tooltip.status' },
                            'fill': { 'value': 'black' },
                            'fontWeight': { 'value': 'bold' }
                        }
                    }
                },
                {
                    'name': 'elapsed',
                    'type': 'text',
                    'properties': {
                        'update': {
                            'x': { 'value': 6 },
                            'y': { 'value': 59 },
                            'text': { 'signal': 'tooltip.elapsed' },
                            'fill': { 'value': 'black' },
                            'fontWeight': { 'value': 'bold' }
                        }
                    }
                }
            ]
        },
        {
            'name': 'statusTooltip',
            'type': 'group',
            'properties': {
                'update': {
                    'x': { 'signal': 'sTooltip.x' },
                    'y': { 'signal': 'sTooltip.y' },
                    'width': { 'signal': 'sTooltip.width' },
                    'height': { 'value': 24 },
                    'fill': { 'value': '#fff' },
                    'fillOpacity': { 'value': 1 },
                    'stroke': { 'value': '#aaa' },
                    'strokeWidth': { 'value': 0.5 }
                }
            },
            'marks': [
                {
                    'name': 'status',
                    'type': 'text',
                    'properties': {
                        'update': {
                            'x': { 'value': 8 },
                            'y': { 'value': 16 },
                            'text': { 'signal': 'sTooltip.status' },
                            'fill': { 'value': 'black' },
                            'fontWeight': { 'value': 'bold' }
                        }
                    }
                }
            ]
        }
    ],
    'legends': [
        {
            'fill': 'color',
            'title': 'timings',
            'offset': -3,
            'properties': {
                'title': {
                    'dx': { 'value': 10 },
                    'fontSize': { 'value': 12 }
                },
                'symbols': {
                    'shape': { 'value': 'square' }
                },
                'labels': {
                    'fontSize': { 'value': 12 }
                }
            }
        }
    ]
};
