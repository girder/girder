const timingHistoryChartConfig = {
    'width': 800,
    'height': 500,
    'autosize': 'fit',
    'data': [
        {
            'name': 'table',
            'values': [
            ],
            'transform': [
                {
                    'type': 'formula',
                    'as': 'adjElapsed',
                    'expr': 'clamp(datum.elapsed/1000,-86400,86400)'
                }
            ]
        },
        {
            'name': 'min_y',
            'values': []
        },
        {
            'name': 'stacked',
            'source': 'table',
            'transform': [
                {
                    'type': 'stack',
                    'groupby': ['id'],
                    'field': 'adjElapsed'
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
                    'fields': ['adjElapsed'],
                    'ops': ['sum'],
                    'as': ['sum_y']
                },
                {
                    'type': 'formula',
                    'as': 'min_y',
                    'expr': 'data("min_y")[0].data'
                }
            ]
        }
    ],
    'scales': [
        {
            'name': 'x',
            'type': 'band',
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
            'scale': 'x',
            'orient': 'bottom',
            'encode': {
                'labels': {
                    'update': {
                        'text': { 'field': 'value', 'scale': 'xlabels' },
                        'angle': { 'value': 50 },
                        'align': { 'value': 'left' },
                        'dy': { 'value': 5 },
                        'dx': { 'value': 7 }
                    }
                }
            }
        },
        {
            'orient': 'left',
            'scale': 'y',
            'format': 's',
            'title': 'seconds',
            'encode': {
                'labels': {
                    'update': {
                        'itemName': { 'value': 'ylabel' }
                    }
                }
            }
        }
    ],
    'signals': [
        {
            'name': 'hover',
            'value': { 'pos': {}, 'datum': {} },
            'on': [
                {
                    'events': '@timing:mousemove',
                    'update': '{ pos: {x: x(), y: y()}, datum:datum}'
                },
                {
                    'events': '@timing:mouseout',
                    'update': '{pos:{},datum:{}}'
                }
            ]
        },
        {
            'name': 'tt0',
            'value': {},
            'update': '{ title:hover.datum.title, updated:hover.datum.updated, status:!hover.datum.status?"":hover.datum.status+":", elapsed:abs(hover.datum["elapsed"]) }'
        },
        {
            'name': 'tt1',
            'value': {},
            'update': '{ elapsed: ' +
                '!tt0.elapsed ? "" : ' +
                'floor(tt0.elapsed/(' +
                '  tt0.elapsed >= 3600000 ? 3600000 : (' +
                '    tt0.elapsed >= 60000 ? 60000 : 1000))) + ' +
                'timeFormat(datetime(0,0,0,0,0,0,tt0.elapsed), ' +
                '  tt0.elapsed >= 3600000 ? ":%M:%S.%L": (' +
                '    tt0.elapsed >= 60000 ? ":%S.%L" : ".%Ls")) }'
        },
        {
            'name': 'tt2',
            'value': {},
            'update': '{ width:!tt0.title?0:max(max(max(tt0.title.length,tt0.status.length),tt1.elapsed.length),tt0.updated.length)*7 }'
        },
        {
            'name': 'tooltip',
            'value': {},
            'update': '{ y:hover.pos.y+30, x:(hover.pos.x>width-tt2.width-5?hover.pos.x-tt2.width-5:hover.pos.x+5), width:tt2.width, title:tt0.title, updated:tt0.updated, status:tt0.status, elapsed:tt1.elapsed }'
        },
        {
            'name': 'sHover',
            'value': { 'pos': {}, 'datum': {} },
            'on': [
                {
                    'events': '@statusmark:mousemove',
                    'update': '{ pos: {x: x(), y: y()}, datum:datum}'
                },
                {
                    'events': '@statusmark:mouseout',
                    'update': '{pos:{},datum:{}}'
                }
            ]
        },
        {
            'name': 'stt0',
            'value': {},
            'update': '{ status:sHover.datum?sHover.datum.currentStatus:"" }'
        },
        {
            'name': 'stt1',
            'value': {},
            'update': '{ width:(stt0.status?stt0.status.length:0)*9 }'
        },
        {
            'name': 'sTooltip',
            'value': {},
            'update': '{ y:sHover.pos.y+30, x:(sHover.pos.x>width-stt1.width-7?sHover.pos.x-stt1.width-5:sHover.pos.x+5), width:stt1.width, status:stt0.status }'
        }
    ],
    'marks': [
        {
            'type': 'rect',
            'name': 'timing',
            'from': {
                'data': 'stacked'
            },
            'encode': {
                'enter': {
                    'x': { 'scale': 'x', 'field': 'id' },
                    'width': { 'scale': 'x', 'band': true, 'offset': -2 },
                    'y': { 'scale': 'y', 'field': 'y0' },
                    'y2': { 'scale': 'y', 'field': 'y1' },
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
            'name': 'statusmarkbase',
            'type': 'rect',
            'from': {
                'data': 'stats'
            },
            'encode': {
                'enter': {
                    'width': { 'scale': 'x', 'band': true, 'offset': -4 },
                    'height': { 'value': 6 },
                    'x': { 'scale': 'x', 'field': 'id', 'offset': 1 },
                    'y': { 'scale': 'y', 'field': 'min_y', 'offset': 9 },
                    'fill': { 'value': 'rgb(204,204,204)' },
                    'itemName': { 'value': 'status' }
                },
                'update': { 'fillOpacity': { 'value': 1 } },
                'hover': {
                    'fillOpacity': { 'value': 0.5 }
                }
            }
        },
        {
            'name': 'statusmark',
            'type': 'rect',
            'from': {
                'data': 'stats'
            },
            'encode': {
                'enter': {
                    'width': { 'scale': 'x', 'band': true, 'offset': -4 },
                    'height': { 'value': 6 },
                    'x': { 'scale': 'x', 'field': 'id', 'offset': 1 },
                    'y': { 'scale': 'y', 'field': 'min_y', 'offset': 9 },
                    'fill': { 'scale': 'color', 'field': 'currentStatus' },
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
            'encode': {
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
                    'encode': {
                        'update': {
                            'x': { 'value': 6 },
                            'y': { 'value': 14 },
                            'text': { 'signal': 'tooltip.title' },
                            'fill': { 'value': 'black' }
                        }
                    }
                },
                {
                    'name': 'updated',
                    'type': 'text',
                    'encode': {
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
                    'encode': {
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
                    'encode': {
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
            'encode': {
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
                    'encode': {
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
            'title': 'Selected Phases',
            'offset': 20,
            'encode': {
                'title': {
                    'update': {
                        'fontSize': { 'value': 12 }
                    }
                },
                'symbols': {
                    'update': {
                        'shape': { 'value': 'square' }
                    }
                },
                'labels': {
                    'update': {
                        'fontSize': { 'value': 12 }
                    }
                }
            }
        }
    ]
};

export default timingHistoryChartConfig;
