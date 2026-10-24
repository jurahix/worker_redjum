//var contextPath = "/redam/servicios/";

//TODO Contexto del Sistema
var contextPath = "/redjum/";

mainApp.factory('Procedimiento001', function($resource) {
	return $resource(contextPath + 'deudoresPorNombres/'+'?hash_id='+Math.random());
});

mainApp.factory('Procedimiento002', function($resource) {
	return $resource(contextPath + 'deudoresPorDocumento/'+'?hash_id='+Math.random());
});

mainApp.factory('Procedimiento003', function($resource) {
	return $resource(contextPath + 'deudoresPorPeriodo/'+'?hash_id='+Math.random());
});

mainApp.factory('Procedimiento004', function($resource) {
	return $resource(contextPath + 'fotoDeudorByte/'+'?hash_id='+Math.random());
});

mainApp.factory('Procedimiento005', function($resource) {
	return $resource(contextPath + 'deudasPorDeudor/'+'?hash_id='+Math.random());
});

mainApp.factory('Procedimiento006', function($resource) {
	return $resource(contextPath + 'tiposDocumentos/'+'?hash_id='+Math.random());
});

mainApp.factory('Procedimiento007', function($resource) {
	return $resource(contextPath + 'deudoresPorRazonSocial/'+'?hash_id='+Math.random());
});

mainApp.factory("ResultadoService", function() {
	return {
		opcion:"",
		criterio:{},
		data: []		
	};
});
//TODO CAL Temporal
mainApp.factory("DetalleService", function() {
	return {
		detalledeudor: {},
		deudas: [],
		imagen: {},
		poseefoto: false		
	};
});