//***********************************************************************************************************************************
//*********************************************** CONTROLADOR PARA CONSULTA *********************************************************
//***********************************************************************************************************************************
mainApp.controller('consultaDeudoresController', function($filter, $scope, $location, $log, $timeout, Notification, Procedimiento001, Procedimiento002, Procedimiento003, Procedimiento006, Procedimiento007, ResultadoService) { 
	
	$log.info('Ingresamos al controlador de consultaDeudoresController');
	
	$scope.exceptionmsg = "Lo sentimos, existen problemas al consultar los datos. Por favor intente nuevamente en unos minutos.";
	
	//************************* MANEJO DE FECHAS CON ANGULARJS  ****************************************//
	var today = new Date();
	var haceUnMes = new Date();
	haceUnMes.setDate(haceUnMes.getDate() - 30);
	
	$scope.maxDate = new Date(today.getFullYear(),today.getMonth() , today.getDate());
	
    $scope.dateOptions = {
	    formatYear: 'yy',
	    maxDate: $scope.maxDate,
	    minDate: null,
	    showWeeks: false,
	    startingDay: 1
    };
    
    $scope.dateOptions2 = {
	    formatYear: 'yy',
	    maxDate: $scope.maxDate,
	    minDate: null,
	    showWeeks: false,
	    startingDay: 1
    };
    
    $scope.toggleMin1 = function() {
//	    $scope.dateOptions.minDate = new Date("01/01/2016");
    };

    $scope.toggleMin2 = function() {
	    $scope.dateOptions2.minDate = new Date($scope.criterio.periodoInicio);	    
//	    var fechaInicio = new Date($scope.criterio.periodoInicio);
//	    fechaInicio.setDate(fechaInicio.getDate() + 90);
//	    
//	    if(fechaInicio > $scope.maxDate){
//	    	 $scope.dateOptions2.maxDate = new Date($scope.criterio.periodoInicio);
//	    }else{
//	    	$scope.dateOptions2.maxDate = new Date(fechaInicio);
//	    }
    };

    /** calendario fecha ini */
    $scope.open1 = function() {
    	$scope.toggleMin1();
    	$scope.popup1.opened = true;
    };

    /** calendario fecha fin */
    $scope.open2 = function() {
    	$scope.popup2.opened = true;    	
    	$scope.toggleMin2();
    };
  
    // formato de fecha	  
    $scope.formato = 'dd/MM/yyyy';  

    $scope.popup1 = {
    	opened: false
    };

    $scope.popup2 = {
    	opened: false
    };	


	//	BUSQUEDA POR NOMBRES Y APELLIDOS
	$scope.criterio = {};
	$scope.criterio.paterno = "";
	$scope.criterio.materno = "";
	$scope.criterio.nombres = "";
	$scope.criterio.captcha = "";
	$scope.criterio.periodoInicio = haceUnMes;
	$scope.criterio.periodoFin = today;
	
	$scope.consultarPorNombres = function(){
		//Validamos los campos obligatorios
		
		if(!$scope.validarFormularioPorNombres()){
			return false;
		}
		
		Procedimiento001.get({ paterno:$scope.criterio.paterno, materno: $scope.criterio.materno, nombres:$scope.criterio.nombres, captcha:$scope.criterio.captcha})
		.$promise.then(
	        //success
	        function( value ){/*Do something with value*/
	        		        	
	        	//Verificamos si existen mensajes de error
        		if(value.error != null && value.error != undefined){
        			$scope.generarCaptcha();
    	    		$scope.mostrarNotificacion("Error", value.error.descripcion, "notificacionMensaje.html", "error");
    	    		
        		}else{
        			//verificamos si existe data
        			if(value.data == null || value.data == undefined){
        				$scope.generarCaptcha();
        				$scope.mostrarNotificacion("Informaci\u00f3n", "Los datos ingresados no presentan registros.", "notificacionMensaje.html", "warning");
        			}else{
        				//Nos vamos a otra pagina
    		        	ResultadoService.opcion = "0";
    		        	ResultadoService.criterio = $scope.criterio;
    		        	ResultadoService.data = value.data;
    		        	
    		        	$location.path("/resultado");
        			}
        		}
	        },
	        //error
	        function( error ){/*Do something with error*/
	        	$scope.generarCaptcha();
	    		$scope.mostrarNotificacion("Error", $scope.exceptionmsg, "notificacionMensaje.html", "error");
	        }
		);
	};
	
	$scope.validarFormularioPorNombres = function(){
		
		if($scope.criterio.paterno == "" && $scope.criterio.materno == "" ){			

			$scope.mostrarNotificacion("Error", "Se requiere alg\u00fan apellido", "notificacionMensaje.html", "error");
			
			return false;
		}
		
		if($scope.criterio.nombres == ""){

			$scope.mostrarNotificacion("Error", "Nombre es requerido", "notificacionMensaje.html", "error");
			return false;
		}
		
		if($scope.criterio.captcha == ""){
			$scope.mostrarNotificacion("Error", "Captcha es requerido", "notificacionMensaje.html", "error");
			return false;
		}
		
		return true;
	};
			
//////////////////////////////////////////////////////////////////////////////////////////////////////////////
	//	BUSQUEDA POR RAZON SOCIAL
	$scope.criterio.razonsocial = "";
	
	$scope.consultarPorRazonSocial = function(){
	
		if(!$scope.validarRazonSocial()){
			return false;
		}
		Procedimiento007.get({ razonsocial:$scope.criterio.razonsocial, captcha:$scope.criterio.captcha})
		.$promise.then(
	        //success
	        function( value ){/*Do something with value*/
	        	//Verificamos si existen mensajes de error
        		if(value.error != null && value.error != undefined){
        			$scope.generarCaptcha();
    	    		$scope.mostrarNotificacion("Error", value.error.descripcion, "notificacionMensaje.html", "error");
        		}else{
        			//verificamos si existe data
        			if(value.data == null || value.data == undefined){
        				$scope.generarCaptcha();
        				$scope.mostrarNotificacion("Informaci\u00f3n", "Los datos ingresados no presentan registros.", "notificacionMensaje.html", "warning");
        			}else{
        				//Nos vamos a otra pagina
    		        	ResultadoService.opcion = "0";
    		        	ResultadoService.criterio = $scope.criterio;
    		        	ResultadoService.data = value.data;
    		        	$location.path("/resultado");
        			}
        		}
	        },
	        //error
	        function( error ){/*Do something with error*/
	        	$scope.generarCaptcha();
	    		$scope.mostrarNotificacion("Error", $scope.exceptionmsg, "notificacionMensaje.html", "error");
	        }
		);
	};
	
	$scope.validarRazonSocial = function(){
		
		if($scope.criterio.razonsocial == ""){			
			$scope.mostrarNotificacion("Error", "Se requiere una razon social ", "notificacionMensaje.html", "error");
			return false;
		}
		if($scope.criterio.captcha == ""){
			$scope.mostrarNotificacion("Error", "Captcha es requerido", "notificacionMensaje.html", "error");
			return false;
		}
		return true;
	};
//////////////////////////////////////////////////////////////////////////////////////////////////////////////
	
	//	BUSQUEDA POR NUMERO DE DOCUMENTO

	//	CARGAMOS LOS DOCUMENTOS
	$scope.cargarTiposDocumento = function() {
		Procedimiento006.query()
		.$promise.then(	
			//success
	        function( value ){/*Do something with value*/
	        	$scope.tiposDocumento = value;
	        },
	        //error
	        function( error ){/*Do something with error*/
	        	$scope.generarCaptcha();
	    		$scope.mostrarNotificacion("Error", $scope.exceptionmsg, "notificacionMensaje.html", "error");
	        }
		);
	};
	
	$scope.cargarTiposDocumento();
	
	$scope.criterio.tipoDocumento = {};
	$scope.criterio.numerodocumento = "";
	
	$scope.consultarPorDocumento = function(){
	
		if(!$scope.validarFormularioPorDocumento()){
			return false;
		}
		
		Procedimiento002.get({ tipoDocumento:$scope.criterio.tipoDocumento.campo, numerodocumento: $scope.criterio.numerodocumento, captcha:$scope.criterio.captcha })
		.$promise.then(
	        //success
	        function( value ){/*Do something with value*/
	        	//Verificamos si existen mensajes de error
	        	if(value.error != null && value.error != undefined){
	        		$scope.generarCaptcha();
	        		$scope.mostrarNotificacion("Error", value.error.descripcion, "notificacionMensaje.html", "error");
	        		
        		}else{
        			//verificamos si existe data
        			if(value.data == null || value.data == undefined){
        				$scope.generarCaptcha();
        				$scope.mostrarNotificacion("Informaci\u00f3n", "Los datos ingresados no presentan registros.", "notificacionMensaje.html", "warning");
        			}else{
        				//Nos vamos a otra pagina
    		        	ResultadoService.opcion = "1";
    		        	ResultadoService.criterio = $scope.criterio;
    		        	ResultadoService.data = value.data;
    		        	
    		        	$location.path("/resultado");
        			}
        		}        		
	        },
	        //error
	        function( error ){/*Do something with error*/
	        	$scope.generarCaptcha();
	    		$scope.mostrarNotificacion("Error", $scope.exceptionmsg, "notificacionMensaje.html", "error");
	        }
		);
	};
	
	$scope.validarFormularioPorDocumento = function(){

		if($scope.criterio.tipoDocumento != null && ($scope.criterio.tipoDocumento.campo == "" || $scope.criterio.tipoDocumento.campo == undefined ) ){

			$scope.mostrarNotificacion("Error", "Tipo de Documento es requerido", "notificacionMensaje.html", "error");			
			return false;
		}
		
		if($scope.criterio.numerodocumento == "" ){
			$scope.mostrarNotificacion("Error", "N\u00famero de Documento es requerido", "notificacionMensaje.html", "error");			
			return false;
		}
		
		if($scope.criterio.captcha == ""){
			$scope.mostrarNotificacion("Error", "Captcha es requerido", "notificacionMensaje.html", "error");			
			return false;
		}

		return true;
	};
	
	//	DEUDORES POR RANGO DE FECHAS
	$scope.consultarPorPeriodo = function(){

		if(!$scope.validarFormularioPorPeriodo()){
			return false;
		}
		
		var fechaI = moment($scope.padStr($scope.criterio.periodoInicio.getFullYear()) + "-" + $scope.padStr(1 + $scope.criterio.periodoInicio.getMonth()) + "-" + $scope.padStr($scope.criterio.periodoInicio.getDate())).format("DD/MM/YYYY HH:mm:ss");
		var fechaF = moment($scope.padStr($scope.criterio.periodoFin.getFullYear()) + "-" + $scope.padStr(1 + $scope.criterio.periodoFin.getMonth()) + "-" + $scope.padStr($scope.criterio.periodoFin.getDate())).format("DD/MM/YYYY HH:mm:ss");
		
		Procedimiento003.get({fechaInicio: fechaI, fechaFin: fechaF, captcha: $scope.criterio.captcha})
		.$promise.then(
			//success
	        function( value ){/*Do something with value*/
	        	//Verificamos si existen mensajes de error
	        	if(value.error != null && value.error != undefined){
	        		$scope.generarCaptcha();
	        		$scope.mostrarNotificacion("Error", value.error.descripcion, "notificacionMensaje.html", "error");
    	    		
        		}else{
        			//verificamos si existe data
        			if(value.data == null || value.data == undefined){
        				$scope.generarCaptcha();
        				$scope.mostrarNotificacion("Informaci\u00f3n", "Los datos ingresados no presentan registros.", "notificacionMensaje.html", "warning");
        			}else{
        				//Nos vamos a otra pagina
    		        	ResultadoService.opcion = "2";
    		        	ResultadoService.criterio = $scope.criterio;
    		        	ResultadoService.data = value.data;
    		        	
    		        	$location.path("/resultado");
        			}
        		}        		
	        },
	        //error
	        function( error ){/*Do something with error*/	        	
	        	$scope.generarCaptcha();
	        	$scope.mostrarNotificacion("Error", $scope.exceptionmsg, "notificacionMensaje.html", "error");
	        }
		);
	};
	
	$scope.validarFormularioPorPeriodo = function(){
		if($scope.criterio.periodoInicio == "" ){

			$scope.mostrarNotificacion("Error", "Fecha de inicio es requerido", "notificacionMensaje.html", "error");			
			return false;
		}
		
		if($scope.criterio.periodoFin == "" ){

			$scope.mostrarNotificacion("Error", "Fecha de fin es requerido", "notificacionMensaje.html", "error");			
			return false;
		}
		
		if($scope.criterio.captcha == ""){

			$scope.mostrarNotificacion("Error", "Captcha es requerido", "notificacionMensaje.html", "error");			
			return false;
		}

		return true;
	};
	
	// --------------------- FUNCIONES GENERALES -------------------- //
	
	$scope.padStr = function (i) {
	    return (i < 10) ? "0" + i : "" + i;
	};
	
	$scope.consultar = function(active){
		
		if(active == 0){
			$scope.consultarPorNombres();
		}else if(active == 1){
			$scope.consultarPorRazonSocial();
		}else if(active == 2){
			$scope.consultarPorDocumento();
		}else if(active == 3){
			$scope.consultarPorPeriodo();
		}
	};
	
	$scope.limpiar = function(active){		
		if(active == 0){			
			$scope.criterio.paterno = "";
			$scope.criterio.materno = "";
			$scope.criterio.nombres = "";
		}else if(active == 1){
			$scope.criterio.razonsocial = "";
		}else if(active == 2){
			$scope.criterio.tipoDocumento = {};
			$scope.criterio.numerodocumento = "";			
		}else if(active == 3){
			$scope.criterio.periodoInicio = haceUnMes;
			$scope.criterio.periodoFin = today;
		}		
	};
	  
    /** Refrescar captcha **/
    $scope.captchaSrc = "Captcha.jpg";
    $scope.refrescarCaptcha = function (event) {
//    	$scope.captchaSrc = "Captcha.jpg"+'?hash_id='+Math.random();
//    	$scope.criterio.captcha = "";
    	$scope.generarCaptcha();
    	event.preventDefault();
    };
    
    $scope.generarCaptcha = function () {
    	$scope.captchaSrc = "Captcha.jpg"+'?hash_id='+Math.random();
    	$scope.criterio.captcha = "";    	
    };
    
    $scope.mostrarNotificacion = function (titulo, mensaje, url, tipo) {
    	$scope.titulo = titulo;
    	
    	if(tipo == "error"){    		
    		Notification.error({message: mensaje, templateUrl: url, scope: $scope});
    	}else if(tipo == "warning"){
    		Notification.warning({message: mensaje, templateUrl: url, scope: $scope});
    	}
    };
    
    $scope.evitarIframe = function(){
    	var insideIframe = window.top !== window.self;
		  
		if(insideIframe){
			$location.path("/iframe");
		} 
    };
    
    $scope.evitarIframe();
    
});

//***********************************************************************************************************************************
//*********************************************** CONTROLADOR PARA RESULTADO ********************************************************
//***********************************************************************************************************************************
mainApp.controller('resultadoConsultaController', function($scope, $uibModal, $http, $location, $log, $timeout, NgTableParams, Notification, Procedimiento005, Procedimiento004, ResultadoService, DetalleService) {
	
	$scope.existeInformacion = function () {
		if(ResultadoService.data.length == 0){
			$location.path("/");
		}		
	};
	
	$scope.existeInformacion();
	
	$scope.exceptionmsg = "Lo sentimos, existen problemas al consultar los datos. Por favor intente nuevamente en unos minutos.";
	$scope.parametrosmensaje = { type: '', title:'' };
	
	$scope.mensaje = {codigo:"", descripcion:""};
	$scope.mensajes = [];	
	
	/** funcion que se utiliza para abrir pantallas modal */    
    $scope.openModal = function (tmpl, ctrl) {

    	var modalInstance = $uibModal.open({
    	      animation: true,
    	      ariaLabelledBy: 'modal-title',
    	      ariaDescribedBy: 'modal-body',
    	      backdrop: 'static',
    	      keyboard: false,
    	      templateUrl: tmpl,//'modalContentLinea.html',
    	      controller: ctrl,//'modalControllerLinea'    	      
    	      resolve: {
    	    	  item: function () {
    	    		  //envio el $scope al controler indicado
    	              return $scope;
    	    	  }
    	      }
    	});
     
      	modalInstance.result.then(function () {

        }, function () {
          $log.info('Modal dismissed at: ' + new Date());
        });
      	
    };
      	
	// DETALLE DEL DEUDOR
	$scope.poseefoto = false;
	$scope.deudas = [];
	
	$scope.verDetalle = function(deudor){		
		$scope.deudor = deudor;
		$scope.obtenerDeudasDeudor();
	};	
	
	$scope.obtenerDeudasDeudor = function () {
		Procedimiento005.get({ id: $scope.deudor.id})
		.$promise.then(
			//success
	        function( value ){/*Do something with value*/
	        	//Verificamos si existen mensajes de error
	        	if(value.error != null && value.error != undefined){
//    	        	$scope.parametrosmensaje.type = "danger";
//    	        	$scope.parametrosmensaje.title = "Errores";
//    	        	$scope.mensajes = value.errores;
//    	    		$scope.openModal('modalMensaje.html','modalAlerta');
	        		$scope.mostrarNotificacion("Error", value.error.descripcion, "notificacionMensaje.html", "error");
    	    		
        		}else{
        			//verificamos si existe data
        			if(value.data == null || value.data == undefined){        				
//        				$scope.parametrosmensaje.type = "warning";
//        	        	$scope.parametrosmensaje.title = "Informaci\u00f3n";
//        	        	
//    					$scope.mensaje.descripcion="Los datos ingresados no presentan registros.";
//    		    		$scope.mensajes.push($scope.mensaje);
//    		    		
//    		    		$scope.openModal('modalMensaje.html','modalAlerta');
        				$scope.mostrarNotificacion("Informaci\u00f3n", "Los datos ingresados no presentan registros.", "notificacionMensaje.html", "warning");
        				
        			}else{
        				$scope.deudasDeudor = value.data;
        	        	$scope.obtenerFotoDeudor();
        			}
        		}
	        },
	        //error
	        function( error ){/*Do something with error*/	        	
//	        	$scope.parametrosmensaje.type = "danger";
//	    		$scope.parametrosmensaje.title = "Errores";
//	    		
//	    		$scope.mensaje.descripcion=$scope.exceptionmsg;
//	    		$scope.mensajes.push($scope.mensaje);
//	    		
//	    		$scope.openModal('modalMensaje.html','modalAlerta');
	        	$scope.mostrarNotificacion("Error", $scope.exceptionmsg, "notificacionMensaje.html", "error");
	        }
		);
	};
	
	$scope.obtenerFotoDeudor = function () {
		Procedimiento004.get({ id: $scope.deudor.id})
		.$promise.then(
			//success
	        function( value ){/*Do something with value*/
	        	//Verificamos si existen mensajes de error
	        	if(value.error != null && value.error != undefined){
//    	        	$scope.parametrosmensaje.type = "danger";
//    	        	$scope.parametrosmensaje.title = "Errores";
//    	        	$scope.mensajes = value.errores;
//    	    		$scope.openModal('modalMensaje.html','modalAlerta');
	        		$scope.mostrarNotificacion("Error", value.error.descripcion, "notificacionMensaje.html", "error");
    	    		
        		}else{
        			//verificamos si existe data 
        			if(value.data[0] != null && value.data[0] != undefined){
        				if(value.data[0].foto != undefined){
        					$scope.fotoDeudor = value.data[0].foto;
        	        		$scope.poseefoto = true;        	        			
        				}else{
        					$scope.poseefoto = false;
        				}
        			}else{
        				$scope.poseefoto = false;
        			}
        			
    	        	$scope.openModal('modalDeudor.html','modalDeudorController');
        			//TODO CAL Temporal
        			//DetalleService.detalledeudor = $scope.deudor;
        			//DetalleService.deudas = $scope.deudasDeudor;
        			//DetalleService.imagen = $scope.fotoDeudor;
        			//DetalleService.poseefoto = $scope.poseefoto;
        			//$location.path("/detalle");
        		}
	        },
	        //error
	        function( error ){/*Do something with error*/	        	
//	        	$scope.parametrosmensaje.type = "danger";
//	    		$scope.parametrosmensaje.title = "Errores";
//	    		
//	    		$scope.mensaje.descripcion=$scope.exceptionmsg;
//	    		$scope.mensajes.push($scope.mensaje);
//	    		
//	    		$scope.openModal('modalMensaje.html','modalAlerta');
	        	$scope.mostrarNotificacion("Error", $scope.exceptionmsg, "notificacionMensaje.html", "error");
	        }
		);
	};
	
	//	CREACION DE LA TABLA	
	$scope.generarTabla = function (listDeudores){
		
		var data = [];
		if(listDeudores.size == 1){			
			data[0] = deudor;
		}else{
			data = listDeudores;
		}
		
		$scope.deudoresTable = new NgTableParams({count: 10},{
			counts: [],
			dataset: data
		});
	};
	
	$scope.regresar = function(){
		$location.path("/");
	};
	
    $scope.mostrarNotificacion = function (titulo, mensaje, url, tipo) {
    	$scope.titulo = titulo;
    	
    	if(tipo == "error"){    		
    		Notification.error({message: mensaje, templateUrl: url, scope: $scope});
    	}else if(tipo == "warning"){
    		Notification.warning({message: mensaje, templateUrl: url, scope: $scope});
    	}
    };
	
	//Cargamos la tabla con los registros obtenidos
	$scope.generarTabla(ResultadoService.data);
	
	$scope.criterio = ResultadoService.criterio;
	
	$scope.opcion = ResultadoService.opcion;
});


//***********************************************************************************************************************************
//*********************************************** CONTROLADOR PARA VENTANAS MODAL ***************************************************
//***********************************************************************************************************************************
mainApp.controller('modalDeudorController', function($scope, $http, $uibModalInstance, item) {

	$scope.detalledeudor = item.deudor;
	$scope.deudas = item.deudasDeudor;
	$scope.imagen = item.fotoDeudor;
	$scope.poseefoto = item.poseefoto;
	
	$scope.closeModal = function () {
		$uibModalInstance.dismiss('closeModal');
	};
});

//***********************************************************************************************************************************
//*********************************************** CONTROLADOR PARA VENTANAS DE ALERTA ***************************************************
//***********************************************************************************************************************************
mainApp.controller('modalAlerta', function($scope, $http, $uibModalInstance, item) {
	$scope.parametrosmensaje = item.parametrosmensaje;
	$scope.mensajes = item.mensajes;
	
	$scope.closeModal = function () {
		$uibModalInstance.dismiss('closeModal');		
	};
	
	$scope.refrescarCaptcha = function (event) {
    	item.captchaSrc = "Captcha.jpg"+'?hash_id='+Math.random();
    	item.criterio.captcha = "";
    	event.preventDefault();
    };
});

//***********************************************************************************************************************************
//*********************************************** CONTROLADOR PARA DETALLE *********************************************************
//***********************************************************************************************************************************
//TODO CAL Temporal
mainApp.controller('detalleDeudoresController', function($scope, DetalleService) { 

	$scope.detalledeudor = DetalleService.detalledeudor;
	$scope.deudas = DetalleService.deudas;
	$scope.imagen = DetalleService.imagen;
	$scope.poseefoto = DetalleService.poseefoto;
	$scope.tp = DetalleService.detalledeudor.tp;
	
});

